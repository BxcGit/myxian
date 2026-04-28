import asyncio
import time
from typing import Optional, Callable, Awaitable
from .xianyu_api import XianyuApis
from ..utils.logger import get_logger

logger = get_logger("xianyu.token_manager", log_file="xianyu.log")

class XianyuTokenManager:
    """Token刷新管理器"""

    def __init__(
        self,
        xianyu_api: XianyuApis,
        device_id: str,
        refresh_interval: int = 3600,
        retry_interval: int = 300,
        on_refreshed: Callable[[], Awaitable[None]] | None = None,
    ):
        self._xianyu_api: XianyuApis = xianyu_api
        self._device_id = device_id
        self._refresh_interval = refresh_interval
        self._retry_interval = retry_interval
        self._current_token: Optional[str] = None
        self._last_refresh_time = 0.0
        self._task: Optional[asyncio.Task] = None
        self._should_restart = False
        self._on_refreshed = on_refreshed

    def update_config(self, refresh_interval: int, retry_interval: int) -> None:
        """更新配置"""
        self._refresh_interval = refresh_interval
        self._retry_interval = retry_interval

    async def refresh(self) -> Optional[str]:
        """刷新token"""
        try:
            logger.info("开始刷新token...")
            result = self._xianyu_api.get_token(self._device_id)

            if 'data' in result and 'accessToken' in result['data']:
                self._current_token = result['data']['accessToken']
                self._last_refresh_time = time.time()
                logger.info("Token刷新成功")
                return self._current_token
            else:
                logger.error(f"Token刷新失败: {result}")
                return None

        except Exception as e:
            logger.error(f"Token刷新异常: {str(e)}")
            return None

    async def run_loop(self) -> None:
        """Token刷新循环"""
        while True:
            try:
                current_time = time.time()
                # 判断token过期没有
                if current_time - self._last_refresh_time >= self._refresh_interval:
                    logger.info("Token即将过期，准备刷新...")
                    new_token = await self.refresh()

                    if new_token:
                        logger.info("Token刷新成功，准备重新建立连接...")
                        self._should_restart = True
                        if self._on_refreshed:
                            await self._on_refreshed()
                        break
                    else:
                        logger.error(f"Token刷新失败，将在{self._retry_interval // 60}分钟后重试")
                        await asyncio.sleep(self._retry_interval)
                        continue

                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Token刷新循环出错: {e}")
                await asyncio.sleep(60)

    @property
    def current_token(self) -> Optional[str]:
        return self._current_token

    @current_token.setter
    def current_token(self, value: str) -> None:
        self._current_token = value

    @property
    def should_restart(self) -> bool:
        return self._should_restart

    def clear_restart_flag(self) -> None:
        self._should_restart = False
