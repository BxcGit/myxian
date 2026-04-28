import time
from typing import Set
from ..utils.logger import get_logger

logger = get_logger("xianyu.manual", log_file="xianyu.log")


class ManualModeManager:
    """人工接管模式管理器（单例模式）- 仅存储状态"""

    _instance: "ManualModeManager | None" = None

    def __init__(self):
        self._conversations: Set[str] = set()
        self._timestamps: dict[str, float] = {}

    @classmethod
    def get_instance(cls) -> "ManualModeManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置实例（用于测试）"""
        cls._instance = None

    def enter(self, chat_id: str) -> None:
        """进入人工接管模式，重置计时器"""
        self._conversations.add(chat_id)
        self._timestamps[chat_id] = time.time()

    def exit(self, chat_id: str) -> None:
        """退出人工接管模式"""
        self._conversations.discard(chat_id)
        self._timestamps.pop(chat_id, None)

    def is_manual_mode(self, chat_id: str, timeout: int = 3600) -> bool:
        """
        检查会话是否处于人工接管模式
        检查是否超时，超时自动退出
        返回: True=人工介入中, False=非人工介入
        """
        if chat_id not in self._conversations:
            return False

        # 检查超时
        if time.time() - self._timestamps[chat_id] > timeout:
            self.exit(chat_id)
            return False

        return True

    def check_trigger(self, message: str, chat_id: str, timeout: int, keywords: str, exit_keywords: str) -> bool:
        """
        检查消息是否触发人工介入/退出，并更新计时
        返回: True=人工介入中, False=非人工介入
        """
        message_stripped = message.strip()
        logger.info(f"检查消息: {exit_keywords} {keywords}")
        # 检查退出关键字
        if exit_keywords and exit_keywords in message_stripped:
            if chat_id in self._conversations:
                self.exit(chat_id)
                logger.info(f"会话 {chat_id} 退出人工接管模式")
            return False

        # 检查进入关键字
        if keywords and keywords in message_stripped:
            self.enter(chat_id)
            logger.info(f"会话 {chat_id} 进入人工接管模式")
            return True

        # 检查当前状态
        return self.is_manual_mode(chat_id, timeout)


# 模块级别单例访问函数
def get_manual_manager() -> ManualModeManager:
    """获取全局人工管理模式管理器实例"""
    return ManualModeManager.get_instance()
