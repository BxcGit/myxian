import sqlite3
from .core.path_utils import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # 用户表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'common',
            manual_timeout INTEGER DEFAULT 3600,
            manual_keywords TEXT DEFAULT '。',
            manual_exit_keywords TEXT DEFAULT '退出'
        )
        """
    )
    # 咸鱼账号表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS xianyu_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            xianyu_name TEXT NOT NULL,
            cookie TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    # 商品表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            xianyu_account_id INTEGER NOT NULL,
            item_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            images TEXT,
            skus TEXT,
            main_prompt TEXT,
            price TEXT,
            FOREIGN KEY (xianyu_account_id) REFERENCES xianyu_accounts(id),
            UNIQUE(xianyu_account_id, item_id)
        )
        """
    )
    # 会话表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            xianyu_account_id INTEGER NOT NULL,
            chat_id TEXT NOT NULL,
            user_id TEXT,
            user_name TEXT,
            item_id TEXT,
            last_message_time INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY (xianyu_account_id) REFERENCES xianyu_accounts(id),
            UNIQUE(xianyu_account_id, chat_id)
        )
        """
    )
    # 消息表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            xianyu_account_id INTEGER NOT NULL,
            is_outgoing INTEGER NOT NULL DEFAULT 0,
            sender_id TEXT,
            sender_name TEXT,
            content TEXT,
            message_type TEXT DEFAULT 'chat',
            created_at INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id),
            FOREIGN KEY (xianyu_account_id) REFERENCES xianyu_accounts(id)
        )
        """
    )
    # 迁移：为 xianyu_accounts 表添加 user_agent 字段
    try:
        cursor.execute("ALTER TABLE xianyu_accounts ADD COLUMN user_agent TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误

    # 迁移：为 users 表添加人工接管配置字段
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN manual_timeout INTEGER DEFAULT 3600")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN manual_keywords TEXT DEFAULT '。'")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN manual_exit_keywords TEXT DEFAULT '退出'")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误

    # 迁移：为 products 表添加新字段
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN item_id TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN title TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN images TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN skus TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN main_prompt TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN price TEXT")
    except sqlite3.OperationalError:
        pass  # 字段已存在，忽略错误

    conn.commit()
    conn.close()
