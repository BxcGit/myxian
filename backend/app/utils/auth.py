from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..database import get_db_connection
from .security import decode_access_token
from .logger import RequestContext

# HTTP Bearer 认证
security = HTTPBearer()


class CurrentUser:
    """当前登录用户"""

    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    依赖项：获取当前登录用户
    从 JWT token 中解析用户信息
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的 token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    username = payload.get("username")

    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token 内容",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 设置用户上下文
    RequestContext.set_user_id(user_id)

    return CurrentUser(user_id=user_id, username=username)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser | None:
    """
    依赖项：获取当前登录用户（可选）
    如果没有 token 返回 None，但不抛异常
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id = payload.get("user_id")
    username = payload.get("username")

    if user_id is None or username is None:
        return None

    # 设置用户上下文
    RequestContext.set_user_id(user_id)

    return CurrentUser(user_id=user_id, username=username)
