import asyncio
import websockets
import logging
from typing import Optional, Callable, Awaitable
import time
import json

from .xianyu_utils import generate_mid
from ..utils.logger import get_logger

logger = get_logger("xianyu.heartbeat", log_file="xianyu.log")
class XianyuHeartbeat:
    """心跳管理器"""

    def __init__(self, interval: int = 15, timeout: int = 5):
        self._interval = interval # 心跳间隔，单位秒
        self._timeout = timeout # 心跳超时时间，单位秒
        self._last_sent = 0.0
        self._last_response = 0.0

    def update_config(self, interval: int, timeout: int) -> None:
        """更新配置"""
        self._interval = interval
        self._timeout = timeout

    async def send_heartbeat(self, ws: websockets.ClientConnection) -> None:
        """发送心跳包"""
        heartbeat_msg = {
            "lwp": "/!",
            "headers": {"mid": generate_mid()}
        }
        await ws.send(json.dumps(heartbeat_msg))
        self._last_sent = time.time()
        logger.debug("心跳包已发送")
    
    def handle_response(self, message_data: dict) -> bool:
        """处理心跳响应"""
        try:
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self._last_response = time.time()
                return True
        except Exception as e:
            logger.error(f"处理心跳响应出错: {e}")
        return False

    async def run_loop(self, ws: websockets.ClientConnection) -> None:
        """心跳维护循环"""
        while True:
            try:
                current_time = time.time()
                if current_time - self._last_sent >= self._interval:
                    logger.info("发送心跳包")
                    await self.send_heartbeat(ws)

                if (current_time - self._last_response) > (self._interval + self._timeout):
                    logger.warning("心跳响应超时，可能连接已断开")
                    break

                await asyncio.sleep(4)
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                break

    def get_last_response_time(self) -> float:
        return self._last_response

    def reset(self) -> None:
        """重置心跳状态"""
        self._last_sent = time.time()
        self._last_response = time.time()
    

