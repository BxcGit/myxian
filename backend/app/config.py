import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

from .core.path_utils import BASE_DIR, DB_PATH, ENV_PATH

load_dotenv(ENV_PATH)


class AIConfig(BaseModel):
    """AI Agent配置"""
    ai_model: str = "gpt-4o-mini"
    ai_api_base: str | None = None
    ai_api_key: str = ""
    ai_timeout: float = 30.0
    ai_max_retries: int = 3
    ai_queue_maxsize: int = 1000
    ai_temperature: float = 0.7
    ai_history_limit: int = 10

    @classmethod
    def from_env(cls) -> "AIConfig":
        """从环境变量加载配置，变量前缀为AI_"""
        return cls(
            ai_model=os.getenv("AI_MODEL", "gpt-4o-mini"),
            ai_api_base=os.getenv("AI_API_BASE") or None,
            ai_api_key=os.getenv("AI_API_KEY", ""),
            ai_timeout=float(os.getenv("AI_TIMEOUT", 30.0)),
            ai_max_retries=int(os.getenv("AI_MAX_RETRIES", 3)),
            ai_queue_maxsize=int(os.getenv("AI_QUEUE_MAXSIZE", 1000)),
            ai_temperature=float(os.getenv("AI_TEMPERATURE", 0.7)),
            ai_history_limit=int(os.getenv("AI_HISTORY_LIMIT", 10)),
        )


class XianyuConfig(BaseModel):
    """咸鱼WebSocket配置"""
    heartbeat_interval: int = 15
    heartbeat_timeout: int = 5
    token_refresh_interval: int = 3600
    token_retry_interval: int = 300
    message_expire_time: int = 3600

    @classmethod
    def from_env(cls) -> "XianyuConfig":
        """从环境变量加载配置"""
        return cls(
            heartbeat_interval=int(os.getenv("XIANYU_HEARTBEAT_INTERVAL", 15)),
            heartbeat_timeout=int(os.getenv("XIANYU_HEARTBEAT_TIMEOUT", 5)),
            token_refresh_interval=int(os.getenv("XIANYU_TOKEN_REFRESH_INTERVAL", 3600)),
            token_retry_interval=int(os.getenv("XIANYU_TOKEN_RETRY_INTERVAL", 300)),
            message_expire_time=int(os.getenv("XIANYU_MESSAGE_EXPIRE_TIME", 3600)),
        )
