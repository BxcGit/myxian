import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# JWT 配置
SECRET_KEY = "your-secret-key-change-in-production"  # 生产环境应从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

# 密码哈希
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """验证并解码 JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度
    返回: (是否通过, 错误消息)
    """
    if len(password) < 8:
        return False, "密码长度至少8位"
    if not re.search(r"[A-Za-z]", password):
        return False, "密码必须包含字母"
    if not re.search(r"\d", password):
        return False, "密码必须包含数字"
    return True, ""


def sha256_hash(password: str) -> str:
    """SHA256 哈希（用于兼容旧数据）"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_sha256(password: str, hashed: str) -> bool:
    """验证 SHA256 哈希（用于兼容旧数据）"""
    return sha256_hash(password) == hashed
