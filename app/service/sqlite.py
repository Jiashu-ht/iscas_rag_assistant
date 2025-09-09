import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# 确保data目录存在
DATA_DIR = Path("dataset/sqlite")
DATA_DIR.mkdir(exist_ok=True)

# 数据库文件路径
DB_PATH = DATA_DIR / "id_mappings.db"

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS talk_document_mappings (
            talk_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (talk_id, document_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS talk_dataset_mappings (
            talk_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 接口 /chat_summary_2 使用
    c.execute('''
        CREATE TABLE IF NOT EXISTS talk_doc_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            talk_id TEXT NOT NULL,
            doc_id TEXT NOT NULL,
            doc_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(talk_id, doc_id) 
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
        c.execute("SELECT client_id, file_name FROM id_mappings WHERE ragflow_id = ?", (ragflow_id,))
        result = c.fetchone()
        if result:
            # 返回两个值：ragflow_id（第0列）和 file_name（第1列）
            return result[0], result[1]
        else:
            # 无结果时返回 (None, None)，避免解包错误
            return None, None

# 初始化数据库（应用启动时调用）
# init_db()

# 新增会话与数据集映射操作函数
def save_talk_dataset_mapping(talk_id, dataset_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO talk_dataset_mappings (talk_id, dataset_id) VALUES (?, ?)",
            (talk_id, dataset_id)
        )
        conn.commit()

def get_dataset_id_by_talk_id(talk_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT dataset_id FROM talk_dataset_mappings WHERE talk_id = ?", (talk_id,))
        result = c.fetchone()
        return result[0] if result else None

# 新增会话与文档映射操作函数
def save_talk_document_mapping(talk_id, document_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO talk_document_mappings (talk_id, document_id) VALUES (?, ?)",
            (talk_id, document_id)
        )
        conn.commit()

def get_document_ids_by_talk_id(talk_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT document_id FROM talk_document_mappings WHERE talk_id = ?", (talk_id,))
        results = c.fetchall()
        return [result[0] for result in results] if results else []
    

# 接口 /chat_summary_2 使用
# 新增保存talk与文档映射的函数
def save_talk_doc_mapping(talk_id: str, doc_id: str, doc_name: str):
    """保存对话ID与文档ID、文档名称的映射关系"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """INSERT OR IGNORE INTO talk_doc_mappings 
               (talk_id, doc_id, doc_name) 
               VALUES (?, ?, ?)""",
            (talk_id, doc_id, doc_name)
        )
        conn.commit()
        # 返回是否插入了新记录
        return c.rowcount > 0

# 接口 /chat_summary_2 使用
# 新增通过talk_id获取关联文档的函数
def get_docs_by_talk_id(talk_id: str) -> list[tuple]:
    """通过对话ID获取关联的所有文档ID和名称，以元组列表形式返回"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT doc_id, doc_name FROM talk_doc_mappings 
               WHERE talk_id = ? 
               ORDER BY created_at DESC""",
            (talk_id,)
        )
        results = c.fetchall()
        return results if results else []
