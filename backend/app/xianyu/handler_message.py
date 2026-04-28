import json
import random
import time
import logging
from typing import Callable

from .parser import XianyuMessageParser
from .xianyu_api import XianyuApis
from ..database import get_db_connection
from .manual_manager import get_manual_manager
from ..utils.logger import get_logger

logger = get_logger("xianyu.handler", log_file="xianyu.log")


def _get_or_create_session(xianyu_account_id: int, chat_id: str, user_id: str | None,
                             user_name: str | None, item_id: str | None,
                             force_update_name: bool = False) -> int:
    """获取或创建会话， 返回session_id

    Args:
        force_update_name: 若为True，则强制用传入的user_name更新会话的user_name（用于卖家消息更新买家占位名）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = int(time.time() * 1000)

    # 尝试查找已存在的会话
    cursor.execute(
        "SELECT id, user_name FROM sessions WHERE xianyu_account_id = ? AND chat_id = ?",
        (xianyu_account_id, chat_id),
    )
    row = cursor.fetchone()

    if row:
        session_id = row["id"]
        existing_name = row["user_name"]

        # 判断是否需要更新user_name：
        # 1. force_update_name=True（卖家消息强制更新）
        # 2. 现有name是以"买家"开头的占位名，且新name是真实用户名（不是None也不是以"买家"开头）
        is_placeholder = existing_name and existing_name.startswith("买家")
        should_update = force_update_name or (is_placeholder and user_name and not user_name.startswith("买家"))

        if should_update:
            cursor.execute(
                "UPDATE sessions SET last_message_time = ?, updated_at = ?, user_id = COALESCE(?, user_id), user_name = ? WHERE id = ?",
                (now, now, user_id, user_name, session_id),
            )
        else:
            cursor.execute(
                "UPDATE sessions SET last_message_time = ?, updated_at = ?, user_id = COALESCE(?, user_id) WHERE id = ?",
                (now, now, user_id, session_id),
            )
    else:
        cursor.execute(
            """INSERT INTO sessions (xianyu_account_id, chat_id, user_id, user_name, item_id, last_message_time, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (xianyu_account_id, chat_id, user_id, user_name, item_id, now, now, now),
        )
        session_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return session_id


def _save_message(session_id: int, xianyu_account_id: int, sender_id: str | None,
                  sender_name: str | None, content: str, message_type: str = "chat",
                  is_outgoing: bool = False) -> None:
    """保存消息到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = int(time.time() * 1000)

    cursor.execute(
        """INSERT INTO messages (session_id, xianyu_account_id, is_outgoing, sender_id, sender_name, content, message_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, xianyu_account_id, int(is_outgoing), sender_id, sender_name, content, message_type, now),
    )
    conn.commit()
    conn.close()


def _get_or_create_product(xianyu_account_id: int, item_id: str, xianyu_api: XianyuApis) -> dict | None:
    """
    获取或创建商品，返回商品信息
    1. 先查数据库
    2. 数据库没有则调用API获取
    3. 保存到数据库
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 先查数据库
    cursor.execute(
        "SELECT * FROM products WHERE xianyu_account_id = ? AND item_id = ?",
        (xianyu_account_id, str(item_id)),
    )
    row = cursor.fetchone()

    if row:
        conn.close()
        return dict(row)

    conn.close()

    # 数据库没有，调用API获取
    api_result = xianyu_api.get_item_info(item_id)
    if not api_result or "data" not in api_result:
        logger.warning(f"获取商品信息失败: {item_id}")
        return None

    item_data = api_result.get("data", {}).get("itemDO", {})
    if not item_data:
        logger.warning(f"商品数据为空: {item_id}")
        return None

    # 解析数据
    title = item_data.get("title", "")
    description = item_data.get("desc", "")
    price = item_data.get("soldPrice", "")  # 商品价格

    # 处理图片列表
    image_infos = item_data.get("imageInfos", [])
    images = json.dumps([img.get("url", "") for img in image_infos])

    # 处理SKU列表（优先用idleItemSkuList）
    sku_list = item_data.get("idleItemSkuList", []) or item_data.get("skuList", [])
    skus = []
    for sku in sku_list:
        sku_info = {
            "skuId": sku.get("skuId"),
            "price": sku.get("price"),
            "propertyText": sku.get("propertyList", [{}])[0].get("valueText", "") if sku.get("propertyList") else "",
            "quantity": sku.get("quantity"),
        }
        skus.append(sku_info)
    skus_json = json.dumps(skus)

    # 保存到数据库
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO products (xianyu_account_id, item_id, title, description, images, skus, main_prompt, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (xianyu_account_id, str(item_id), title, description, images, skus_json, "", price),
        )
        conn.commit()
        product_id = cursor.lastrowid

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        result = dict(row) if row else None
    except Exception as e:
        logger.error(f"保存商品失败: {e}")
        result = None
    finally:
        conn.close()

    return result


class XianyuMessageHandler:
    """消息处理类"""
    def __init__(
        self,
        xianyu_api: XianyuApis,
        xianyu_account_id: int,
        myid: str | None,
        message_expire_time: int = 3600,
        user_id: int | None = None,
        username: str = "",
        manual_timeout: int = 3600,
        manual_keywords: str = "。",
        manual_exit_keywords: str = "退出",
        ws_send_callback: Callable | None = None,
    ):
        self._xianyu_api = xianyu_api
        self._xianyu_account_id = xianyu_account_id
        self._myid = myid
        self._parser = XianyuMessageParser()
        self.message_expire_time = message_expire_time
        # 用户配置
        self._user_id = user_id
        self._username = username
        self._manual_timeout = manual_timeout
        self._manual_keywords = manual_keywords
        self._manual_exit_keywords = manual_exit_keywords
        # WebSocket发送回调工厂 (sync callable: text -> None)
        # factory must be: Callable[[chatid: str, toid: str], Callable[[str], None]]
        self._ws_send_callback_factory = ws_send_callback
    
    async def handle(
        self,
        message_data: dict,
    ) -> bool:
        """
        处理消息
        返回: 是否已处理（True表示已处理，不再继续）
        """
        try:
            # 检查同步包
            if not self._parser.is_sync_package(message_data):
                logger.info(f"非同步包消息，跳过: {message_data.get('lwp', 'unknown')}")
                return True

            # 获取并解密数据
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]
            if "data" not in sync_data:
                logger.info("同步包中无data字段")
                return True

            decrypted = self._parser.decrypt_message(sync_data)
            if not decrypted:
                logger.info(f"消息解密失败，原始sync_data: {sync_data}")
                return True

            message = decrypted
            # 检查订单消息
            order_status = self._parser.is_order_message(message)
            # 订单消息处理
            if order_status:
                await self.order_message(message, order_status)
                return True
            else:
                # 检查消息类型
                if self._parser.is_typing_status(message):
                    logger.info("用户正在输入")
                    return True
                
                if not self._parser.is_chat_message(message):
                    logger.info("其他非聊天消息")
                    return True
                # logger.info("聊天消息")
                # logger.info(message)
                await self.handle_user_message(message)
                return True

        except Exception as e:
            logger.error(f"处理消息时发生错误: {str(e)}")
            logger.debug(f"原始消息: {message_data}")
            return False

    # TODO: 订单消息处理
    async def order_message(self, message: dict, order_status: str) -> bool:
        """处理订单消息"""
        parsed = self._parser.parse_chat_message(message)
        if not parsed:
            return True

        send_user_id = parsed["send_user_id"]
        send_message = parsed["send_message"]
        send_user_name = parsed["send_user_name"]
        url_info = parsed["url_info"]
        item_id = self._parser.extract_item_id(url_info)
        chat_id = self._parser.extract_chat_id(message["1"]["2"])

        user_url = f'https://www.goofish.com/personal?userId={send_user_id}'

        # 保存会话
        session_id = _get_or_create_session(
            self._xianyu_account_id, chat_id, send_user_id,
            send_user_name, item_id, force_update_name=True
        )

        # 保存订单消息
        _save_message(
            session_id=session_id,
            xianyu_account_id=self._xianyu_account_id,
            sender_id=send_user_id,
            sender_name=send_user_name,
            content=f"[订单状态] {order_status}: {send_message}",
            message_type="order",
            is_outgoing=False,
        )

        # TODO 自动处理订单
        logger.info(f'订单状态: {order_status} - {user_url}')
        return True

    async def handle_user_message(self, message: dict) -> bool:
        """处理用户聊天消息"""
        # 解析聊天消息
        parsed = self._parser.parse_chat_message(message)
        if not parsed:
            return True

        create_time = parsed["create_time"]
        send_user_name = parsed["send_user_name"]
        send_user_id = parsed["send_user_id"]
        send_message = parsed["send_message"]
        url_info = parsed["url_info"]

        # 时效性验证
        if (time.time() * 1000 - create_time) > self.message_expire_time:
            1776003460519
            logger.debug(f"{time.time() * 1000} 消息创建时间 {create_time} 已创建 {create_time} 已过期，丢弃")
            logger.debug(f"{time.time() * 1000 - create_time}")
            return True

        # 提取商品ID和会话ID
        item_id = self._parser.extract_item_id(url_info)
        chat_id = self._parser.extract_chat_id(message["1"]["2"])

        if not item_id:
            logger.warning("无法获取商品ID")
            return True

        # 获取或创建商品信息（先查数据库，没有则调用API获取并保存）
        product = _get_or_create_product(self._xianyu_account_id, item_id, self._xianyu_api)
        if product:
            logger.info(f"商品信息: {product.get('title')}, SKU数: {len(json.loads(product.get('skus', '[]')))}")

        # 检查系统消息
        if self._parser.is_bracket_system_message(send_message):
            logger.info(f"检测到系统消息：'{send_message}'，跳过自动回复")
            return True

        # 先持久化消息
        session_id = self.persist_info(chat_id, send_user_id, send_user_name, item_id, send_message)

        # 判断是本人发的还是别人发的
        is_self = self._myid == send_user_id
        manual_manager = get_manual_manager()

        if is_self:
            # 自己发的消息：检查是否触发关键词进入/退出人工接管模式
            if manual_manager.check_trigger(
                send_message, chat_id,
                timeout=self._manual_timeout,
                keywords=self._manual_keywords,
                exit_keywords=self._manual_exit_keywords
            ):
                logger.info(f"会话 {chat_id} 触发人工接管模式")
                return True
        else:
            # 别人发的消息：检查是否处于人工接管模式
            if manual_manager.is_manual_mode(chat_id, timeout=self._manual_timeout):
                logger.info(f"会话 {chat_id} 处于人工接管中，不处理")
                return True

        logger.info(f"用户: {send_user_name} (ID: {send_user_id}), 商品: {item_id}, 会话: {chat_id}, 消息: {send_message}")

        # 投递给AI Agent处理（不阻塞WebSocket handler）
        if self._ws_send_callback_factory is not None:
            ws_callback = self._ws_send_callback_factory(chat_id, send_user_id)
            try:
                from ..ai_agent import get_agent
                agent = await get_agent()
                await agent.enqueue(
                    chatid=chat_id,
                    message=send_message,
                    session_id=session_id,
                    sender_id=self._myid,
                    xianyu_account_id=self._xianyu_account_id,
                    ws_callback=ws_callback,
                )
            except RuntimeError as e:
                logger.warning(f"AI Agent not available: {e}")
            except Exception as e:
                logger.error(f"Failed to enqueue to AI Agent: {e}", exc_info=True)

        return True
    # 持久化信息
    def persist_info(self, chat_id, send_user_id, send_user_name, item_id, send_message) -> int:
        """持久化信息，返回session_id"""
        is_self = self._myid == send_user_id

        # 如果是自己发的消息，sender_name 设为"买家+随机数"
        if is_self:
            sender_name = f"买家{random.randint(1000, 9999)}"
        else:
            sender_name = send_user_name

        # 保存会话
        session_id = _get_or_create_session(
            self._xianyu_account_id, chat_id, send_user_id,
            sender_name, item_id, force_update_name=False
        )

        _save_message(
            session_id=session_id,
            xianyu_account_id=self._xianyu_account_id,
            sender_id=send_user_id,
            sender_name=sender_name,
            content=send_message,
            message_type="chat",
            is_outgoing=is_self,
        )
        return session_id
