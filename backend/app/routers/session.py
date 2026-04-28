import time
from fastapi import APIRouter, HTTPException, Depends
from ..database import get_db_connection
from ..models.session import SessionCreate, SessionUpdate, SessionResponse
from ..models.message import MessageCreate, MessageResponse
from ..utils.auth import get_current_user, CurrentUser
from ..xianyu.manual_manager import get_manual_manager
from ..xianyu.account_context import AccountContext
from ..utils.logger import get_logger

logger = get_logger("session", log_file="app.log")

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _check_account_permission(xianyu_account_id: int, user_id: int) -> bool:
    """检查用户是否有权限操作指定账号"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM xianyu_accounts WHERE id = ?",
        (xianyu_account_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return False
    return row["user_id"] == user_id


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    xianyu_account_id: int | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取所有会话，可按账号ID筛选（只返回当前用户的）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if xianyu_account_id:
        # 校验账号权限
        if not _check_account_permission(xianyu_account_id, current_user.user_id):
            conn.close()
            raise HTTPException(status_code=403, detail="无权限访问此账号")
        cursor.execute(
            "SELECT * FROM sessions WHERE xianyu_account_id = ? ORDER BY updated_at DESC",
            (xianyu_account_id,),
        )
    else:
        # 获取当前用户所有账号的会话
        cursor.execute(
            """
            SELECT s.* FROM sessions s
            LEFT JOIN xianyu_accounts a ON s.xianyu_account_id = a.id
            WHERE a.user_id = ?
            ORDER BY s.updated_at DESC
            """,
            (current_user.user_id,),
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取指定会话"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Session not found")

    # 权限校验
    if not _check_account_permission(row["xianyu_account_id"], current_user.user_id):
        raise HTTPException(status_code=403, detail="无权限访问此会话")

    return dict(row)


@router.post("/", response_model=SessionResponse)
async def create_session(
    session: SessionCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """创建或更新会话"""
    # 校验账号权限
    conn = get_db_connection()
    if not _check_account_permission(session.xianyu_account_id, current_user.user_id):
        conn.close()
        raise HTTPException(status_code=403, detail="无权限操作此账号")
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    now = int(time.time() * 1000)

    # 尝试插入，如果已存在则更新
    cursor.execute(
        """
        INSERT INTO sessions (xianyu_account_id, chat_id, user_id, user_name, item_id, last_message_time, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session.xianyu_account_id, session.chat_id, session.user_id, session.user_name,
         session.item_id, now, now, now),
    )
    session_id = cursor.lastrowid

    # 如果插入失败（已存在），则更新
    if cursor.rowcount == 0:
        cursor.execute(
            """
            UPDATE sessions SET user_id = COALESCE(?, user_id),
                user_name = COALESCE(?, user_name),
                item_id = COALESCE(?, item_id),
                last_message_time = ?,
                updated_at = ?
            WHERE xianyu_account_id = ? AND chat_id = ?
            """,
            (session.user_id, session.user_name, session.item_id, now, now,
             session.xianyu_account_id, session.chat_id),
        )
        cursor.execute(
            "SELECT * FROM sessions WHERE xianyu_account_id = ? AND chat_id = ?",
            (session.xianyu_account_id, session.chat_id),
        )
        row = cursor.fetchone()
        session_id = row["id"]

    conn.commit()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    update: SessionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新会话"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 先获取会话信息校验权限
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    if not _check_account_permission(row["xianyu_account_id"], current_user.user_id):
        conn.close()
        raise HTTPException(status_code=403, detail="无权限修改此会话")

    now = int(time.time() * 1000)

    if update.last_message_time is not None:
        cursor.execute(
            "UPDATE sessions SET last_message_time = ?, updated_at = ? WHERE id = ?",
            (update.last_message_time, now, session_id),
        )

    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()

    return dict(row)


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取指定会话的消息"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 先获取会话信息校验权限
    cursor.execute("SELECT xianyu_account_id FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    if not _check_account_permission(row["xianyu_account_id"], current_user.user_id):
        conn.close()
        raise HTTPException(status_code=403, detail="无权限访问此会话")

    cursor.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ? OFFSET ?",
        (session_id, limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/{session_id}/last-message")
async def get_session_last_message(
    session_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取指定会话的最后一条消息（用于会话列表预览）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT xianyu_account_id FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    if not _check_account_permission(row["xianyu_account_id"], current_user.user_id):
        conn.close()
        raise HTTPException(status_code=403, detail="无权限访问此会话")

    cursor.execute(
        "SELECT content, created_at FROM messages WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
        (session_id,),
    )
    msg_row = cursor.fetchone()
    conn.close()
    if not msg_row:
        return {"content": "", "created_at": None}
    return dict(msg_row)


@router.post("/messages", response_model=MessageResponse)
async def create_message(
    message: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """创建消息并更新会话时间，如果是人工接管消息则发送到闲鱼"""
    # 校验账号权限
    conn = get_db_connection()
    if not _check_account_permission(message.xianyu_account_id, current_user.user_id):
        conn.close()
        raise HTTPException(status_code=403, detail="无权限操作此账号")
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    now = int(time.time() * 1000)

    cursor.execute(
        """
        INSERT INTO messages (session_id, xianyu_account_id, is_outgoing, sender_id, sender_name, content, message_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (message.session_id, message.xianyu_account_id, int(message.is_outgoing),
         message.sender_id, message.sender_name, message.content, message.message_type, now),
    )
    message_id = cursor.lastrowid

    # 更新会话的最后消息时间
    cursor.execute(
        "UPDATE sessions SET last_message_time = ?, updated_at = ? WHERE id = ?",
        (now, now, message.session_id),
    )

    conn.commit()

    # 获取会话信息（用于WebSocket发送）
    cursor.execute("SELECT chat_id, user_id FROM sessions WHERE id = ?", (message.session_id,))
    session_row = cursor.fetchone()
    chat_id = session_row["chat_id"] if session_row else None
    to_user_id = session_row["user_id"] if session_row else None

    # 获取发送消息用户的配置
    cursor.execute(
        "SELECT manual_timeout, manual_keywords, manual_exit_keywords FROM users WHERE id = ?",
        (current_user.user_id,),
    )
    user_row = cursor.fetchone()
    manual_timeout = user_row["manual_timeout"] if user_row else 3600
    manual_keywords = user_row["manual_keywords"] if user_row else "。"
    manual_exit_keywords = user_row["manual_exit_keywords"] if user_row else "退出"

    # 获取消息记录用于返回
    cursor.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
    msg_row = cursor.fetchone()
    conn.close()

    # 初始化发送状态
    send_status = None

    if chat_id and to_user_id:
        manual_manager = get_manual_manager()

        if message.is_outgoing:
            # 卖家发送的消息：检查是否触发退出人工接管
            check_result = manual_manager.check_trigger(
                message.content, chat_id,
                timeout=manual_timeout,
                keywords=manual_keywords,
                exit_keywords=manual_exit_keywords
            )
            # 如果还在人工模式中，发送消息后退出
            if check_result and manual_manager.is_manual_mode(chat_id, timeout=manual_timeout):
                manual_manager.exit(chat_id)
                logger.info(f"会话 {chat_id} 退出人工接管模式（卖家发送消息）")
            # 发送消息到闲鱼
            send_status = await _send_to_xianyu(message.xianyu_account_id, chat_id, to_user_id, message.content)
        else:
            # 买家发送的消息：检查是否触发进入人工接管
            check_result = manual_manager.check_trigger(
                message.content, chat_id,
                timeout=manual_timeout,
                keywords=manual_keywords,
                exit_keywords=manual_exit_keywords
            )
            if check_result:
                logger.info(f"会话 {chat_id} 进入人工接管模式（买家发送消息）")
                send_status = "skipped"  # 人工接管中，跳过发送
            else:
                # 不在人工接管模式，发送到闲鱼WebSocket
                send_status = await _send_to_xianyu(message.xianyu_account_id, chat_id, to_user_id, message.content)

    response_data = dict(msg_row) if msg_row else {"id": message_id}
    if send_status:
        response_data["send_status"] = send_status
    return response_data


async def _send_to_xianyu(xianyu_account_id: int, chat_id: str, to_user_id: str, text: str):
    """通过WebSocket发送消息到闲鱼，返回发送状态"""
    client = AccountContext.get_client(xianyu_account_id)
    if not client or not client._ws:
        logger.warning(f"账号 {xianyu_account_id} 的WebSocket未连接，无法发送消息")
        return "failed"

    try:
        await client.send_message(client._ws, chat_id, to_user_id, text)
        logger.info(f"消息已发送至闲鱼: chat_id={chat_id}, to_user_id={to_user_id}")
        return "sent"
    except Exception as e:
        logger.error(f"发送消息到闲鱼失败: {e}")
        return "failed"


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除会话及其关联消息"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 先获取会话信息校验权限
    cursor.execute("SELECT xianyu_account_id FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Session not found")

    if not _check_account_permission(row["xianyu_account_id"], current_user.user_id):
        conn.close()
        raise HTTPException(status_code=403, detail="无权限删除此会话")

    # 先删除关联的消息
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    # 再删除会话
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"msg": "Session deleted successfully"}


@router.get("/messages/recent", response_model=list[MessageResponse])
async def get_recent_messages(
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取最近的所有消息（只返回当前用户的）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.* FROM messages m
        LEFT JOIN xianyu_accounts a ON m.xianyu_account_id = a.id
        WHERE a.user_id = ?
        ORDER BY m.created_at DESC
        LIMIT ?
        """,
        (current_user.user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
