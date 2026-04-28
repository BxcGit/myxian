import logging
import sys
import json
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
import uuid


# 日志目录
from ..core.path_utils import LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)


class JsonFormatter(logging.Formatter):
    """JSON 格式化器 - 结构化日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加 request_id（如果存在）
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # 添加 user_id（如果存在）
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        # 添加 extra 字段
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_data, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """普通格式化器 - 人类可读"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def get_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    use_json: bool = False,
) -> logging.Logger:
    """
    获取配置好的 logger

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 可选，指定日志文件
        use_json: 是否使用 JSON 格式

    Returns:
        配置好的 logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # 不向上传播，避免重复

    # 清除已有 handler
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    if use_json:
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(PlainFormatter())
    logger.addHandler(console_handler)

    # File handler (带轮转)
    if log_file:
        file_handler = RotatingFileHandler(
            LOG_DIR / log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(JsonFormatter())
        logger.addHandler(file_handler)

    return logger


class RequestContext:
    """请求上下文 - 管理请求级别的日志字段"""

    _request_id: Optional[str] = None
    _user_id: Optional[int] = None

    @classmethod
    def set_request_id(cls, request_id: Optional[str] = None) -> str:
        """设置请求 ID"""
        cls._request_id = request_id or str(uuid.uuid4())[:8]
        return cls._request_id

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        return cls._request_id

    @classmethod
    def set_user_id(cls, user_id: Optional[int]) -> None:
        """设置用户 ID"""
        cls._user_id = user_id

    @classmethod
    def get_user_id(cls) -> Optional[int]:
        return cls._user_id

    @classmethod
    def clear(cls) -> None:
        """清除上下文"""
        cls._request_id = None
        cls._user_id = None


class LoggerAdapter(logging.LoggerAdapter):
    """带上下文的 Logger 适配器"""

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})

        # 添加 request_id
        if RequestContext.get_request_id():
            extra["request_id"] = RequestContext.get_request_id()

        # 添加 user_id
        if RequestContext.get_user_id():
            extra["user_id"] = RequestContext.get_user_id()

        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(name: str, level: int = logging.INFO) -> LoggerAdapter:
    """
    获取带上下文的 logger

    用法:
        logger = get_context_logger(__name__)
        logger.info("message")  # 自动带上 request_id 和 user_id
    """
    base_logger = logging.getLogger(name)
    base_logger.setLevel(level)
    return LoggerAdapter(base_logger, {})


# 预配置的 logger
# API logger - 用于 API 请求/响应追踪
api_logger = get_context_logger("api", logging.INFO)

# WebSocket logger
ws_logger = get_logger("xianyu.ws", logging.INFO, "ws.log")

# Auth logger
auth_logger = get_logger("auth", logging.INFO, "auth.log")

# Error logger - 只记录 ERROR 及以上
error_logger = get_logger("error", logging.ERROR, "error.log", use_json=True)
