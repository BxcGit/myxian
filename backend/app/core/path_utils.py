"""路径管理工具 - 支持开发模式和打包模式"""

import sys
import os
from pathlib import Path


def get_base_dir() -> Path:
    """
    获取基础目录
    - 打包模式: 可执行文件所在目录
    - 开发模式: backend 目录的父目录 (项目根目录)
    """
    if getattr(sys, 'frozen', False):
        # 打包模式: sys.frozen 为 True
        return Path(sys.executable).parent
    else:
        # 开发模式: 项目根目录 (backend/app/core -> backend/app -> backend -> 父目录)
        return Path(__file__).parent.parent.parent.parent


BASE_DIR = get_base_dir()

# 数据库路径
DB_PATH = BASE_DIR / "user.db"

# 环境配置文件
ENV_PATH = BASE_DIR / ".env"

# Prompts 目录
PROMPTS_DIR = BASE_DIR / "prompts"

# 日志目录
LOG_DIR = BASE_DIR / "logs"

# 前端静态文件目录 (用于打包后)
STATIC_DIR = BASE_DIR / "static"


def ensure_dirs():
    """确保必要的目录存在"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


def is_frozen() -> bool:
    """是否处于打包模式"""
    return getattr(sys, 'frozen', False)