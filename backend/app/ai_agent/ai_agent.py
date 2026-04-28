"""AI Agent — 全局单例，自动回复消息处理器"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Callable

from openai import AsyncOpenAI
from openai import APIError as OpenAIAPIError

from ..core.path_utils import PROMPTS_DIR
from ..config import AIConfig
from ..database import get_db_connection
from ..utils.logger import get_logger


def _save_ai_message(session_id: int, xianyu_account_id: int, sender_id: str,
                     sender_name: str, content: str) -> None:
    """将AI回复消息保存到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = int(time.time() * 1000)
    cursor.execute(
        """INSERT INTO messages (session_id, xianyu_account_id, is_outgoing, sender_id, sender_name, content, message_type, created_at)
        VALUES (?, ?, 1, ?, ?, ?, 'chat', ?)""",
        (session_id, xianyu_account_id, sender_id, sender_name, content, now),
    )
    conn.commit()
    conn.close()

logger = get_logger("ai_agent", log_file="xianyu.log")

# ---------------------------------------------------------------------------
# System prompt loading
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    """从文件加载系统提示词"""
    prompt_path = PROMPTS_DIR / "system_prompt.txt"

    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to load system prompt from {prompt_path}: {e}")
        # 返回默认提示词
        return "你是一个专业的闲鱼二手商品卖家客服，回复顾客关于商品的问题。"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AIMessage:
    """enqueue 时传入的消息信封"""
    chatid: str
    message: str
    session_id: int
    sender_id: str
    xianyu_account_id: int
    ws_callback: Callable[[str], None]
    created_at: float = field(default_factory=time.time)


@dataclass
class AIResponse:
    """AI生成的回复"""
    content: str
    session_id: int
    chatid: str
    generated_at: float = field(default_factory=time.time)


@dataclass
class AIConversationContext:
    """会话上下文 — 商品信息 + 历史消息"""
    session_id: int
    item_id: str | None = None
    product_title: str | None = None
    product_description: str | None = None
    product_price: str | None = None
    recent_messages: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AIAgent
# ---------------------------------------------------------------------------


class AIAgent:
    """全局唯一AI Agent，嵌入阻塞队列，消费消息并调用OpenAI回复"""

    def __init__(self, config: AIConfig | None = None):
        self._config = config or AIConfig.from_env()
        self._queue: asyncio.Queue[AIMessage] = asyncio.Queue(
            maxsize=self._config.ai_queue_maxsize
        )
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._consumer_task: asyncio.Task | None = None
        self._client: AsyncOpenAI | None = None
        self._started: bool = False
        self._system_prompt: str = _load_system_prompt()
        logger.info(f"AI Agent instance created: id={id(self)}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def enqueue(
        self,
        chatid: str,
        message: str,
        session_id: int,
        sender_id: str,
        xianyu_account_id: int,
        ws_callback: Callable[[str], None],
    ) -> None:
        """将消息投入队列（供WebSocket handler调用，非阻塞）"""
        if not self._started:
            logger.debug("AI Agent not started, skipping enqueue")
            return
        msg = AIMessage(
            chatid=chatid,
            message=message,
            session_id=session_id,
            sender_id=sender_id,
            xianyu_account_id=xianyu_account_id,
            ws_callback=ws_callback,
        )
        await self._queue.put(msg)
        logger.info(
            f"Enqueued message chatid={chatid} session_id={session_id}",
            extra={"extra_data": {"chatid": chatid, "session_id": session_id}},
        )

    async def start(self) -> asyncio.Task | None:
        """启动消费者循环（在main.py lifespan中调用）"""
        if not self._config.ai_api_key:
            logger.warning("AI_API_KEY is not set; AI Agent skipped (graceful degradation). Set AI_API_KEY to enable auto-reply.")
            return None
        self._shutdown_event.clear()
        self._client = AsyncOpenAI(
            api_key=self._config.ai_api_key,
            base_url=self._config.ai_api_base,
            timeout=self._config.ai_timeout,
            max_retries=self._config.ai_max_retries,
        )
        self._consumer_task = asyncio.create_task(
            self._consume_loop(), name="ai-agent-consume"
        )
        self._started = True
        logger.info(
            f"AI Agent started, queue maxsize={self._config.ai_queue_maxsize}",
            extra={"extra_data": {
                "model": self._config.ai_model,
                "queue_maxsize": self._config.ai_queue_maxsize,
            }},
        )
        return self._consumer_task


    async def shutdown(self) -> None:
        """优雅关闭：等待队列排空后取消消费者任务"""
        if not self._started:
            return
        logger.info("AI Agent shutting down, draining queue...")
        self._shutdown_event.set()
        # 等待队列排空（最多等待10秒）
        try:
            await asyncio.wait_for(self._queue.join(), timeout=10.0)
            logger.info("Queue drained successfully")
        except asyncio.TimeoutError:
            logger.warning("Queue drain timed out, forcing shutdown")
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("AI Agent shutdown complete")

    # ------------------------------------------------------------------
    # Consumer loop
    # ------------------------------------------------------------------

    async def _consume_loop(self) -> None:
        """持续从队列取出消息并处理，异常不扩散"""
        while not self._shutdown_event.is_set():
            try:
                # 用短 timeout 让事件循环能处理取消信号
                msg = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                await self._process_message(msg)
                self._queue.task_done()
            except asyncio.TimeoutError:
                continue  # 队列空，重新检查 shutdown 事件
            except asyncio.CancelledError:
                break  # 收到取消信号，立即退出

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _strip_thinking(content: str) -> str:
        """移除AI回复中的思考内容，仅保留用户可见部分"""
        import re
        # 移除 <think>...</think>（Claude / Qwen 等）
        content = re.sub(r"<think>[\s\S]*?</think>", "", content)
        # 移除 <thinking>...</thinking>
        content = re.sub(r"<thinking>[\s\S]*?</thinking>", "", content, flags=re.IGNORECASE)
        return content.strip()

    # ------------------------------------------------------------------

    async def _process_message(self, msg: AIMessage) -> None:
        """处理单条消息：验证 → 构建prompt → 调用AI → 发送回复"""
        logger.info(
            f"AI Agent processing message chatid={msg.chatid}",
            extra={"extra_data": {"chatid": msg.chatid, "session_id": msg.session_id}},
        )

        # 跳过空消息
        if not msg.message.strip():
            logger.warning(
                f"Empty message, skipping chatid={msg.chatid}",
                extra={"extra_data": {"chatid": msg.chatid}},
            )
            return

        try:
            # 构建对话消息列表
            messages = await self._build_messages(msg)
            response_content = await self._call_openai(messages)

            if not response_content:
                logger.warning(f"Empty AI response for chatid={msg.chatid}")
                return

            # 过滤掉思考内容（如<think>...），仅保留用户可见回复
            response_content = self._strip_thinking(response_content)
            if not response_content:
                logger.warning(f"AI response empty after stripping thinking content, chatid={msg.chatid}")
                return

            # 通过回调发送回复（ws_callback 是同步的，直接调用即可）
            try:
                msg.ws_callback(response_content)
                # 保存AI回复到消息表
                _save_ai_message(
                    session_id=msg.session_id,
                    xianyu_account_id=msg.xianyu_account_id,
                    sender_id=msg.sender_id,
                    sender_name="AI助手",
                    content=response_content,
                )
                logger.info(
                    f"AI Response sent: {len(response_content)} chars, chatid={msg.chatid}",
                    extra={"extra_data": {
                        "chatid": msg.chatid,
                        "session_id": msg.session_id,
                        "response_len": len(response_content),
                    }},
                )
            except Exception as cb_err:
                logger.error(
                    f"WS callback failed for chatid={msg.chatid}: {cb_err}",
                    exc_info=True,
                    extra={"extra_data": {"chatid": msg.chatid, "session_id": msg.session_id}},
                )

        except Exception as e:
            logger.error(
                f"Failed to process message chatid={msg.chatid}: {e}",
                exc_info=True,
                extra={"extra_data": {"chatid": msg.chatid, "session_id": msg.session_id}},
            )

    async def _build_messages(self, msg: AIMessage) -> list[dict]:
        """构建发送给OpenAI的消息列表（system + history + current）"""
        context = await self._get_conversation_context(msg.session_id)

        # 从文件加载的系统提示词，填充商品信息
        # 转换SKU价格单位：分 -> 元
        product_skus_formatted = "无"
        if context.product_skus and context.product_skus != "无":
            try:
                import json
                skus = json.loads(context.product_skus)
                for sku in skus:
                    if "price" in sku:
                        sku["price"] = sku["price"] / 100  # 分转元
                product_skus_formatted = json.dumps(skus, ensure_ascii=False)
            except Exception:
                product_skus_formatted = context.product_skus
        system_content = self._system_prompt.format(
            product_title=context.product_title or "无",
            product_description=context.product_description or "无",
            product_price=context.product_price or "无",
            product_sku=product_skus_formatted,
            main_prompt=context.product_main_prompt or "无",
        )

        messages: list[dict] = [{"role": "system", "content": system_content}]

        # 历史消息
        for m in context.recent_messages:
            messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})

        # 当前消息
        messages.append({"role": "user", "content": msg.message})

        return messages

    # ------------------------------------------------------------------
    # OpenAI API
    # ------------------------------------------------------------------

    async def _call_openai(self, messages: list[dict]) -> str:
        """调用OpenAI Chat Completions API，返回回复文本"""
        try:
            response = await self._client.chat.completions.create(
                model=self._config.ai_model,
                messages=messages,
                temperature=self._config.ai_temperature,
            )
            return response.choices[0].message.content or ""
        except asyncio.TimeoutError:
            logger.error(
                f"OpenAI request timed out after {self._config.ai_timeout}s",
                extra={"extra_data": {"timeout": self._config.ai_timeout}},
            )
            raise
        except OpenAIAPIError as e:
            logger.error(
                f"OpenAI API error: {e}",
                exc_info=True,
                extra={"extra_data": {"error": str(e)}},
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error calling OpenAI: {e}",
                exc_info=True,
                extra={"extra_data": {"error": str(e)}},
            )
            raise

    # ------------------------------------------------------------------
    # Context retrieval
    # ------------------------------------------------------------------

    async def _get_conversation_context(self, session_id: int) -> AIConversationContext:
        """从数据库获取会话上下文（商品信息 + 最近N条消息）"""

        def _sync_fetch():
            conn = get_db_connection()
            cursor = conn.cursor()
            ctx = AIConversationContext(session_id=session_id)

            # 查会话，获取item_id和xianyu_account_id（用于过滤商品查询）
            cursor.execute(
                "SELECT item_id, xianyu_account_id FROM sessions WHERE id = ?",
                (session_id,),
            )
            xianyu_account_id = None
            row = cursor.fetchone()
            if row:
                ctx.item_id = row["item_id"]
                xianyu_account_id = row["xianyu_account_id"]

            # 查商品（按item_id和xianyu_account_id过滤，保证用户数据隔离）
            if ctx.item_id and xianyu_account_id:
                cursor.execute(
                    "SELECT title, description, price, skus, main_prompt FROM products WHERE item_id = ? AND xianyu_account_id = ?",
                    (str(ctx.item_id), xianyu_account_id),
                )
                prod_row = cursor.fetchone()
                if prod_row:
                    ctx.product_title = prod_row["title"]
                    ctx.product_description = prod_row["description"]
                    ctx.product_price = prod_row["price"]
                    ctx.product_skus = prod_row["skus"]
                    ctx.product_main_prompt = prod_row["main_prompt"]

            # 查最近消息
            cursor.execute(
                f"""SELECT content, is_outgoing, sender_name, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?""",
                (session_id, self._config.ai_history_limit),
            )
            msg_rows = cursor.fetchall()
            ctx.recent_messages = [
                {
                    "role": "assistant" if r["is_outgoing"] else "user",
                    "content": r["content"],
                    "created_at": r["created_at"],
                }
                for r in msg_rows
            ]

            conn.close()
            return ctx

        return await asyncio.to_thread(_sync_fetch)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_agent_instance: AIAgent | None = None
_agent_init_lock: asyncio.Lock = asyncio.Lock()


async def get_agent() -> AIAgent:
    """返回全局AI Agent单例，未初始化或未启动时抛出RuntimeError"""
    if _agent_instance is None:
        raise RuntimeError("AI Agent not initialized. Call get_agent() after app startup.")
    if not _agent_instance._started:
        raise RuntimeError("AI Agent not started. Set AI_API_KEY to enable the agent.")
    return _agent_instance


async def set_agent(agent: AIAgent) -> None:
    """设置全局AI Agent单例（带锁保护）"""
    async with _agent_init_lock:
        global _agent_instance
        _agent_instance = agent
    """返回全局AI Agent单例，未初始化时抛出RuntimeError"""
    if _agent_instance is None:
        raise RuntimeError("AI Agent not initialized. Call get_agent() after app startup.")
    return _agent_instance