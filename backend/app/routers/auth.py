import sqlite3
from fastapi import APIRouter, HTTPException, Depends

from ..database import get_db_connection
from ..models.user import RegisterRequest, LoginRequest, LoginResponse, UserSettings, UserSettingsUpdate
from ..utils.security import (
    hash_password, verify_password, create_access_token,
    validate_password_strength, verify_sha256
)
from ..utils.auth import get_current_user, CurrentUser
from ..utils.logger import get_logger

logger = get_logger("auth", log_file="auth.log")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(req: RegisterRequest):
    # 验证密码强度
    # is_valid, error_msg = validate_password_strength(req.password)
    # if not is_valid:
    #     logger.warning(f"注册失败 - 密码强度不足: {req.username}")
    #     raise HTTPException(status_code=400, detail=error_msg)

    conn = get_db_connection()
    cursor = conn.cursor()
    logger.info(f"注册尝试 {req.username} {req.password}")
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (req.username, hash_password(req.password)),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        logger.warning(f"注册失败 - 用户名已存在: {req.username}")
        raise HTTPException(status_code=400, detail="用户名已存在")
    conn.close()

    # 延迟导入避免循环依赖
    from ..xianyu.account_context import AccountContext
    AccountContext.reload_users()

    logger.info(f"用户注册成功", extra={"extra_data": {"user_id": user_id, "username": req.username}})
    return {"msg": "注册成功"}


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    logger.info(f"登录尝试", extra={"extra_data": {"username": req.username}})

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (req.username,)
        )
        row = cursor.fetchone()
    except Exception as e:
        conn.close()
        logger.error(f"数据库查询失败", extra={"extra_data": {"error": str(e), "username": req.username}})
        raise HTTPException(status_code=500, detail="数据库错误")
    conn.close()

    if row is None:
        logger.warning(f"登录失败 - 用户不存在", extra={"extra_data": {"username": req.username}})
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    user_id, username, password_hash = row["id"], row["username"], row["password_hash"]

    # 兼容旧 SHA256 哈希
    if len(password_hash) == 64:
        if not verify_sha256(req.password, password_hash):
            logger.warning(f"登录失败 - 密码错误", extra={"extra_data": {"user_id": user_id, "username": username}})
            raise HTTPException(status_code=400, detail="用户名或密码错误")
    else:
        if not verify_password(req.password, password_hash):
            logger.warning(f"登录失败 - 密码错误", extra={"extra_data": {"user_id": user_id, "username": username}})
            raise HTTPException(status_code=400, detail="用户名或密码错误")

    # 生成 JWT token
    access_token = create_access_token(data={"user_id": user_id, "username": username})

    logger.info(f"登录成功", extra={"extra_data": {"user_id": user_id, "username": username}})

    return LoginResponse(
        access_token=access_token,
        user_id=user_id,
        username=username,
    )


@router.get("/settings/{username}", response_model=UserSettings)
async def get_user_settings(
    username: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取用户设置"""
    # 权限校验：只能查看自己的设置
    if current_user.username != username:
        logger.warning(f"获取设置失败 - 无权限", extra={"extra_data": {"current_user": current_user.username, "target_user": username}})
        raise HTTPException(status_code=403, detail="无权限访问")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, manual_timeout, manual_keywords, manual_exit_keywords FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        logger.error(f"获取设置失败 - 用户不存在", extra={"extra_data": {"username": username}})
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserSettings(**dict(row))


@router.put("/settings/{username}", response_model=UserSettings)
async def update_user_settings(
    username: str,
    settings: UserSettingsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新用户设置"""
    # 权限校验：只能修改自己的设置
    if current_user.username != username:
        logger.warning(f"更新设置失败 - 无权限", extra={"extra_data": {"current_user": current_user.username, "target_user": username}})
        raise HTTPException(status_code=403, detail="无权限修改")

    # 延迟导入避免循环依赖
    from ..xianyu.account_context import AccountContext

    conn = get_db_connection()
    cursor = conn.cursor()

    # 先检查用户是否存在
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone() is None:
        conn.close()
        logger.error(f"更新设置失败 - 用户不存在", extra={"extra_data": {"username": username}})
        raise HTTPException(status_code=404, detail="用户不存在")

    updates = []
    params = []
    if settings.manual_timeout is not None:
        updates.append("manual_timeout = ?")
        params.append(settings.manual_timeout)
    if settings.manual_keywords is not None:
        updates.append("manual_keywords = ?")
        params.append(settings.manual_keywords)
    if settings.manual_exit_keywords is not None:
        updates.append("manual_exit_keywords = ?")
        params.append(settings.manual_exit_keywords)

    if updates:
        params.append(username)
        cursor.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE username = ?",
            params,
        )
        conn.commit()
        AccountContext.reload_users()

    # 获取更新后的数据
    cursor.execute(
        "SELECT id, username, manual_timeout, manual_keywords, manual_exit_keywords FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()

    logger.info(f"更新设置成功", extra={"extra_data": {"user_id": current_user.user_id, "username": username}})

    return UserSettings(**dict(row))
