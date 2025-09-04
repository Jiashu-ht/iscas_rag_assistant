import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# 确保data目录存在
DATA_DIR = Path("dataset/sqlite")
DATA_DIR.mkdir(exist_ok=True)

# 数据库文件路径
DB_PATH = DATA_DIR / "id_mapping.db"

# 数据库初始化
def init_db():
    # 初始化数据库
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS id_mappings (
            client_id TEXT PRIMARY KEY,
            ragflow_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# 上下文管理器用于数据库连接
@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# 保存映射
def save_mapping(client_id, ragflow_id, file_name):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO id_mappings (client_id, ragflow_id, file_name) VALUES (?, ?, ?)",
            (client_id, ragflow_id, file_name)
        )
        conn.commit()

# 查询映射
def get_ragflow_id_by_client_id(client_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT ragflow_id FROM id_mappings WHERE client_id = ?", (client_id,))
        result = c.fetchone()
        return result[0] if result else None
    
def get_other_by_ragflow_id(ragflow_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT ragflow_id, file_name FROM id_mappings WHERE ragflow_id = ?", (ragflow_id,))
        result = c.fetchone()
        return result[0] if result else None

# 初始化数据库（应用启动时调用）
init_db()