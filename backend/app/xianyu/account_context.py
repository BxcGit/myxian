import asyncio
import json
from typing import Dict, Optional
from ..database import get_db_connection
from .ws_client import WSClient
from ..models.xianyu_account import XianyuAccount
from ..config import XianyuConfig
from ..utils.logger import get_logger

logger = get_logger("xianyu.account_context", log_file="xianyu.log")


class AccountContext:
    """全局账号上下文管理器，负责管理所有闲鱼账号和对应的WebSocket客户端（单例模式）"""

    _instance: "AccountContext | None" = None

    def __init__(self):
        self._user_dict: Dict[int, dict] = {}
        self._account_dict: Dict[int, XianyuAccount] = {}
        self._ws_client_dict: Dict[int, WSClient] = {}
        self._active_account_ids: set[int] = set()
        self._config: XianyuConfig = None
        self._initialized: bool = False

    @classmethod
    def get_instance(cls) -> "AccountContext":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(cls, config: Optional[XianyuConfig] = None) -> None:
        """初始化账号上下文，从数据库加载所有账号"""
        instance = cls.get_instance()
        if instance._initialized:
            logger.warning("AccountContext already initialized")
            return

        instance._config = config or XianyuConfig.from_env()
        logger.info(f"Config: {instance._config}")
        logger.info(f"Message_expire_time: {instance._config.message_expire_time}")
        instance._load_users()
        instance._load_accounts()
        instance._initialized = True
        logger.info(f"AccountContext initialized: {len(instance._account_dict)} accounts loaded")

    def _load_users(self) -> None:
        """从数据库加载所有用户"""
        try:
            logger.info("Loading users from database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, manual_timeout, manual_keywords, manual_exit_keywords FROM users")
            rows = cursor.fetchall()
            for row in rows:
                self._user_dict[row["id"]] = dict(row)
            conn.close()
            logger.info(f"Loaded {len(self._user_dict)} users")
        except Exception as e:
            logger.error(f"Failed to load users: {e}", exc_info=True)

    @classmethod
    def reload_users(cls) -> None:
        """重新从数据库加载用户"""
        instance = cls.get_instance()
        instance._user_dict.clear()
        instance._load_users()

    def _load_accounts(self) -> None:
        """从数据库加载所有闲鱼账号"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, user_id, xianyu_name, cookie, user_agent FROM xianyu_accounts")
            rows = cursor.fetchall()
            for row in rows:
                data = dict(row)
                # 防止 user_agent 为 NULL 被 Pydantic 拒绝
                data.setdefault("user_agent", "")
                account = XianyuAccount(**data)
                self._account_dict[account.id] = account
            conn.close()
            logger.info(f"Loaded {len(self._account_dict)} xianyu accounts")
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}", exc_info=True)

    @classmethod
    async def start_all_clients(cls) -> None:
        """启动所有账号的WebSocket客户端"""
        instance = cls.get_instance()
        if not instance._initialized:
            cls.initialize()

        for account_id, account in instance._account_dict.items():
            if account_id not in instance._ws_client_dict and account.cookie:
                try:
                    await instance.start_client_for_account(account)
                except Exception as e:
                    logger.error(f"Failed to start client for account {account.id}: {e}", exc_info=True)

    async def start_client_for_account(self, account: XianyuAccount) -> Optional[WSClient]:
        """为指定账号启动WebSocket客户端"""
        if not account.cookie:
            logger.warning(f"Account {account.id} has no cookie, skipping")
            return None

        try:
            # 从cookie中提取unb作为用户ID
            cookies = trans_cookies(account.cookie)
            unb = cookies.get('unb', str(account.id))

            # 获取用户配置
            user_info = self._user_dict.get(account.user_id, {})
            manual_timeout = user_info.get("manual_timeout", 3600)
            manual_keywords = user_info.get("manual_keywords", "。")
            manual_exit_keywords = user_info.get("manual_exit_keywords", "退出")

            # 创建并启动客户端
            device_id = generate_device_id(unb)
            logger.info(f"用户信息: {json.dumps(user_info)}")
            logger.info(f"退出关键字: {manual_keywords} {manual_exit_keywords}")
            client = WSClient(
                cookies_str=account.cookie,
                device_id=device_id,
                config=self._config,
                xianyu_account_id=account.id,
                user_agent=account.user_agent,
                user_id=account.user_id,
                username=user_info.get("username", ""),
                manual_timeout=manual_timeout,
                manual_keywords=manual_keywords,
                manual_exit_keywords=manual_exit_keywords,
            )
            client.start()

            self._ws_client_dict[account.id] = client
            self._active_account_ids.add(account.id)
            logger.info(f"Started WS client for account {account.id} ({account.xianyu_name})")
            return client
        except Exception as e:
            logger.error(f"Failed to create WS client for account {account.id}: {e}", exc_info=True)
            return None

    @classmethod
    async def start_account(cls, account_id: int) -> bool:
        """启动指定账号的WebSocket客户端"""
        instance = cls.get_instance()
        account = instance._account_dict.get(account_id)
        if not account:
            logger.warning(f"Account {account_id} not found in context")
            return False
        if account_id in instance._active_account_ids:
            logger.info(f"Account {account_id} already active")
            return True
        client = await instance.start_client_for_account(account)
        return client is not None

    @classmethod
    async def stop_account(cls, account_id: int) -> bool:
        """停止指定账号的WebSocket客户端"""
        instance = cls.get_instance()
        if account_id not in instance._active_account_ids:
            logger.info(f"Account {account_id} is not active")
            return True
        client = instance._ws_client_dict.pop(account_id, None)
        if client:
            try:
                await client.stop()
                logger.info(f"Stopped WS client for account {account_id}")
            except Exception as e:
                logger.error(f"Error stopping client for account {account_id}: {e}")
        instance._active_account_ids.discard(account_id)
        return True

    @classmethod
    async def stop_all_clients(cls) -> None:
        """停止所有WebSocket客户端"""
        instance = cls.get_instance()
        for account_id, client in list(instance._ws_client_dict.items()):
            try:
                await client.stop()
                logger.info(f"Stopped WS client for account {account_id}")
            except Exception as e:
                logger.error(f"Error stopping client for account {account_id}: {e}", exc_info=True)
        instance._ws_client_dict.clear()
        instance._active_account_ids.clear()

    @classmethod
    def add_account(cls, account: XianyuAccount) -> None:
        """添加一个新账号（不会自动启动客户端）"""
        instance = cls.get_instance()
        instance._account_dict[account.id] = account
        logger.info(f"Added account {account.id} ({account.xianyu_name})")

    @classmethod
    def update_account(cls, account: XianyuAccount) -> None:
        """更新账号信息（会重启对应的客户端）"""
        instance = cls.get_instance()
        old_account = instance._account_dict.get(account.id)
        instance._account_dict[account.id] = account

        # 如果cookie变化了，重启客户端
        if old_account and old_account.cookie != account.cookie:
            asyncio.create_task(instance._restart_client(account.id))

        logger.info(f"Updated account {account.id} ({account.xianyu_name})")

    @classmethod
    async def remove_account(cls, account_id: int) -> None:
        """移除账号并停止对应的客户端"""
        instance = cls.get_instance()
        if account_id in instance._ws_client_dict:
            client = instance._ws_client_dict.pop(account_id)
            try:
                await client.stop()
            except Exception as e:
                logger.error(f"Error stopping client for account {account_id}: {e}", exc_info=True)

        instance._active_account_ids.discard(account_id)

        if account_id in instance._account_dict:
            account = instance._account_dict.pop(account_id)
            logger.info(f"Removed account {account_id} ({account.xianyu_name})")

    @classmethod
    def get_account(cls, account_id: int) -> Optional[XianyuAccount]:
        """获取指定ID的账号"""
        instance = cls.get_instance()
        return instance._account_dict.get(account_id)

    @classmethod
    def get_all_accounts(cls) -> list[XianyuAccount]:
        """获取所有账号"""
        instance = cls.get_instance()
        return list(instance._account_dict.values())

    @classmethod
    def get_client(cls, account_id: int) -> Optional[WSClient]:
        """获取指定账号的WebSocket客户端"""
        instance = cls.get_instance()
        return instance._ws_client_dict.get(account_id)

    @classmethod
    def get_all_clients(cls) -> Dict[int, WSClient]:
        """获取所有WebSocket客户端"""
        instance = cls.get_instance()
        return instance._ws_client_dict.copy()

    @classmethod
    def is_account_active(cls, account_id: int) -> bool:
        """检查指定账号是否已启动"""
        instance = cls.get_instance()
        return account_id in instance._active_account_ids

    @classmethod
    def get_active_account_ids(cls) -> set[int]:
        """获取所有已启动的账号ID"""
        instance = cls.get_instance()
        return instance._active_account_ids.copy()

    @classmethod
    def is_initialized(cls) -> bool:
        """检查是否已初始化"""
        instance = cls.get_instance()
        return instance._initialized

    async def _restart_client(self, account_id: int) -> None:
        """重启指定账号的客户端"""
        # 停止旧客户端
        if account_id in self._ws_client_dict:
            try:
                await self._ws_client_dict[account_id].stop()
            except Exception as e:
                logger.error(f"Error stopping old client for account {account_id}: {e}", exc_info=True)
            self._ws_client_dict.pop(account_id, None)

        # 启动新客户端
        account = self._account_dict.get(account_id)
        if account and account.cookie:
            await self.start_client_for_account(account)

    @classmethod
    async def shutdown(cls) -> None:
        """关闭整个上下文，清理资源"""
        instance = cls.get_instance()
        await cls.stop_all_clients()
        instance._account_dict.clear()
        instance._user_dict.clear()
        instance._initialized = False
        logger.info("AccountContext shutdown complete")


# 导入需要的辅助函数（在这里导入避免循环依赖）
from .xianyu_utils import trans_cookies, generate_device_id
