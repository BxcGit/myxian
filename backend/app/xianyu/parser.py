import logging
import json
import base64
from typing import Optional

from .xianyu_utils import decrypt
from ..utils.logger import get_logger

logger = get_logger("xianyu.parser", log_file="xianyu.log")


class XianyuMessageParser:
    """消息解析器 - 负责解析和验证各类消息"""

    @staticmethod
    def is_sync_package(message_data: dict) -> bool:
        """判断是否为同步包消息"""
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False

    @staticmethod
    def is_typing_status(message: dict) -> bool:
        """判断是否为用户正在输入状态消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], list)
                and len(message["1"]) > 0
                and isinstance(message["1"][0], dict)
                and "1" in message["1"][0]
                and isinstance(message["1"][0]["1"], str)
                and "@goofish" in message["1"][0]["1"]
            )
        except Exception:
            return False

    @staticmethod
    def is_chat_message(message: dict) -> bool:
        """判断是否为用户聊天消息"""
        try:
            return (
                isinstance(message, dict)
                and "1" in message
                and isinstance(message["1"], dict)
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False

    @staticmethod
    def is_bracket_system_message(message: str) -> bool:
        """检查是否为带中括号的系统消息"""
        if not message or not isinstance(message, str):
            return False
        clean_message = message.strip()
        return clean_message.startswith('[') and clean_message.endswith(']')

    @staticmethod
    def is_order_message(message: dict) -> Optional[str]:
        """判断是否为订单消息，返回订单状态或None"""
        try:
            if message.get("3", {}).get("redReminder") in [
                "等待买家付款", "交易关闭", "等待卖家发货"
            ]:
                return message["3"]["redReminder"]
        except Exception:
            pass
        return None

    @staticmethod
    def parse_chat_message(message: dict) -> Optional[dict]:
        """解析聊天消息，返回解析后的数据或None"""
        try:
            return {
                "create_time": int(message["1"]["5"]),
                "send_user_name": message["1"]["10"]["reminderTitle"],
                "send_user_id": message["1"]["10"]["senderUserId"],
                "send_message": message["1"]["10"]["reminderContent"],
                "url_info": message["1"]["10"]["reminderUrl"],
            }
        except Exception:
            return None

    @staticmethod
    def extract_item_id(url_info: str) -> Optional[str]:
        """从URL中提取商品ID"""
        if "itemId=" in url_info:
            return url_info.split("itemId=")[1].split("&")[0]
        return None

    @staticmethod
    def extract_chat_id(from_field: str) -> str:
        """从from字段提取会话ID"""
        return from_field.split('@')[0]

    @staticmethod
    def decrypt_message(sync_data: dict) -> Optional[dict]:
        """解密消息"""
        try:
            data = sync_data["data"]
            try:
                data = base64.b64decode(data).decode("utf-8")
                return json.loads(data)
            except Exception:
                decrypted_data = decrypt(data)
                return json.loads(decrypted_data)
        except Exception as e:
            logger.error(f"消息解密失败: {e}")
            return None