import asyncio
import time
import websockets
import json
import base64
from typing import Callable
from ..config import XianyuConfig
from .handler_message import XianyuMessageHandler
from .heart_beat import XianyuHeartbeat
from .token_manager import XianyuTokenManager
from .xianyu_api import XianyuApis
from .xianyu_utils import (
    generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt
)
from ..utils.logger import get_logger

logger = get_logger("xianyu.ws_client", log_file="xianyu.log")

# 配置：外部 WebSocket 服务地址（改为你实际要连接的服务）

class TokenRefreshError(Exception):
    """当 Token 刷新失败时抛出"""
    pass


class WSClient:
    BASE_URL = 'wss://wss-goofish.dingtalk.com/'

    def __init__(
        self,
        cookies_str: str,
        device_id: str,
        config: XianyuConfig,
        xianyu_account_id: int = 0,
        user_agent: str = "",
        user_id: int | None = None,
        username: str = "",
        manual_timeout: int = 3600,
        manual_keywords: str = "。",
        manual_exit_keywords: str = "退出",
    ):
        # 运行所需要的参数
        self._cookies_str = cookies_str
        self._cookies = trans_cookies(cookies_str)
        self._device_id = device_id
        self._user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        self._stop_flag = False
        self._tasks: list[asyncio.Task] = []
        self._heartbeat = None
        self._token_manager = None
        self._api = None
        self._myid = self._cookies.get('unb', '')
        self._device_id = generate_device_id(self._myid) if self._myid else device_id
        # 连接、初始化、心跳维护循环
        self._ws: websockets.ClientConnection = None
        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._message_handler = None
        self._config = config
        self._xianyu_account_id = xianyu_account_id
        self._task: asyncio.Task = None
        # 用户配置
        self._user_id = user_id
        self._username = username
        self._manual_timeout = manual_timeout
        self._manual_keywords = manual_keywords
        self._manual_exit_keywords = manual_exit_keywords
        self.init()

    def init(self):
        """初始化参数"""
        self._api = XianyuApis(user_agent=self._user_agent)
        self._api.session.cookies.update(self._cookies)

        self._heartbeat = XianyuHeartbeat(
            interval=self._config.heartbeat_interval,
            timeout=self._config.heartbeat_timeout
        )

        self._token_manager = XianyuTokenManager(
            xianyu_api=self._api,
            device_id=self._device_id,
            refresh_interval=self._config.token_refresh_interval,
            retry_interval=self._config.token_retry_interval
        )
        self._message_handler = XianyuMessageHandler(
            xianyu_api=self._api,
            xianyu_account_id=self._xianyu_account_id,
            myid=self._myid,
            message_expire_time=self._config.message_expire_time,
            user_id=self._user_id,
            username=self._username,
            manual_timeout=self._manual_timeout,
            manual_keywords=self._manual_keywords,
            manual_exit_keywords=self._manual_exit_keywords,
            ws_send_callback=self._make_sync_send_callback(),
        )

    def _make_sync_send_callback(self):
        """创建同步回调工厂，用于AI Agent发送回复（不阻塞WebSocket handler）

        Returns a sync callable that takes (text: str) and schedules
        an async send_message on the event loop via call_soon.
        """
        def make_callback(chat_id: str, to_user_id: str):
            def sync_wrapper(text: str) -> None:
                if self._ws is None:
                    return
                # 使用预先保存的 event loop 调度异步发送，不依赖 get_running_loop
                self._loop.call_soon(
                    lambda: asyncio.create_task(
                        self.send_message(self._ws, chat_id, to_user_id, text)
                    )
                )
            return sync_wrapper

        return make_callback

        
    

    async def connect(self) -> websockets.ClientConnection:
        """建立WebSocket连接"""
        headers = {
            "Cookie": self._cookies_str,
            "Host": "wss-goofish.dingtalk.com",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": self._user_agent,
            "Origin": "https://www.goofish.com",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        self._ws = await websockets.connect(self.BASE_URL, additional_headers=headers)
        return self._ws
    
    async def initConnect(self, ws: websockets.ClientConnection) -> None:
        """初始化连接（注册）"""
         # 初始化token
        token = self._token_manager.current_token
        if not token:
            logger.error("无法获取有效token，初始化失败")
            raise TokenRefreshError("Token刷新返回空")

        msg = {
            "lwp": "/reg",
            "headers": {
                "cache-header": "app-key token ua wv",
                "app-key": "444e9908a51d1cb236a27862abc769c9",
                "token": token,
                "ua": self._user_agent,
                "dt": "j",
                "wv": "im:3,au:3,sy:6",
                "sync": "0,0;0;0;",
                "did": self._device_id,
                "mid": generate_mid()
            }
        }

        await ws.send(json.dumps(msg))
        await asyncio.sleep(1)

        msg = {
            "lwp": "/r/SyncStatus/ackDiff",
            "headers": {"mid": "5701741704675979 0"},
            "body": [{
                "pipeline": "sync", "tooLong2Tag": "PNM,1", "channel": "sync", "topic": "sync",
                "highPts": 0, "pts": int(time.time() * 1000) * 1000, "seq": 0,
                "timestamp": int(time.time() * 1000)
            }]
        }
        await ws.send(json.dumps(msg))
        logger.info('连接注册完成')
    
    async def send_message(self, ws: websockets.ClientConnection, cid: str, toid: str, text: str) -> None:
        """发送聊天消息"""
        content = {
            "contentType": 1,
            "text": {"text": text}
        }
        text_base64 = str(base64.b64encode(json.dumps(content).encode('utf-8')), 'utf-8')
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {"mid": generate_mid()},
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{cid}@goofish",
                    "conversationType": 1,
                    "content": {
                        "contentType": 101,
                        "custom": {"type": 1, "data": text_base64}
                    },
                    "redPointPolicy": 0,
                    "extension": {"extJson": "{}"},
                    "ctx": {"appVersion": "1.0", "platform": "web"},
                    "mtags": {},
                    "msgReadStatusSetting": 1
                },
                {
                    "actualReceivers": [f"{toid}@goofish", f"{self._device_id}@goofish"]
                }
            ]
        }
        await ws.send(json.dumps(msg))

    async def send_ack(self, ws: websockets.ClientConnection, message_data: dict) -> None:
        """发送ACK响应"""
        try:
            ack = {
                "code": 200,
                "headers": {
                    "mid": message_data["headers"].get("mid", generate_mid()),
                    "sid": message_data["headers"].get("sid", ""),
                }
            }
            for key in ["app-key", "ua", "dt"]:
                if key in message_data["headers"]:
                    ack["headers"][key] = message_data["headers"][key]
            await ws.send(json.dumps(ack))
        except Exception:
            pass
    
    async def _connect_loop(self):
        # 1. 初始化重试间隔和最大间隔
        retry_count = 2
        max_retry_delay = 5
        while not self._stop_flag:
            try:
                # 初始化token
                if not self._token_manager.current_token:
                    token = await self._token_manager.refresh()
                    if not token:
                        logger.error("无法获取有效token")
                        await asyncio.sleep(5)
                        continue
                self._ws = await self.connect()
                await self.initConnect(self._ws)
                # 重置心跳
                self._heartbeat.reset()
                # 启动心跳任务
                heartbeat_task = asyncio.create_task(
                    self._heartbeat.run_loop(self._ws)
                )
                self._tasks.append(heartbeat_task)

                token_task = asyncio.create_task(self._token_manager.run_loop())
                self._tasks.append(token_task)
                 # 主消息循环
                while not self._stop_flag:
                    try:
                        # 处理出站消息
                        # outbound_task = asyncio.create_task(self._handle_outbound_messages(ws))
                        # 接收消息
                        logger.info("等待接收消息...")
                        message = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
                       
                        # 解析消息
                        message_data = json.loads(message)

                        # 处理心跳响应
                        if self._heartbeat.handle_response(message_data):
                            # logger.info("心跳心跳响应已处理")
                            continue

                        logger.info(f"收到消息+1")
                        # 收到消息就发送ACK
                        await self.send_ack(self._ws, message_data)
                        # 调试：打印原始消息结构
                        # 处理消息
                        await self._message_handler.handle(message_data)
                        if self._stop_flag:
                            break  # 连接已关闭，跳出循环

                    except asyncio.TimeoutError:
                        logger.warning("接收消息超时, 继续等待...")
                        if self._stop_flag:
                            break
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket连接已关闭, 重连中...")
                        break
                    except Exception as e:
                        logger.error(f"处理消息时发生错误: {str(e)}")
                    # 清理任务
                for task in self._tasks:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                self._tasks.clear()
            except TokenRefreshError as e:
                logger.error(f"Token刷新失败: {e}, 重试中...")
                if retry_count > 0:
                    retry_count -= 1
                    await asyncio.sleep(max_retry_delay)
                else:
                    break
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"WebSocket error: {e}, reconnecting in 5s...")
            finally:
                if self._ws:
                    await self._ws.close()
                    self._ws = None

    def start(self):
        self._stop_flag = False
        self._task = asyncio.create_task(self._connect_loop())
        logger.info("WebSocket client started")

    async def stop(self):
        self._stop_flag = True
        # 关闭 WebSocket 连接，触发 recv() 抛出 ConnectionClosed
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        # 等待 task 退出（最多 5 秒）
        if self._task:
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        logger.info("WebSocket client stopped")

    def send(self, message: str):
        # 暂不支持外部调用，后续可扩展
        pass
