import sqlite3
import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db.sqlite")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn

def init_db():
    """
    Initializes the SQLite database tables if they do not exist.
    """
    logger.info(f"Initializing SQLite database at '{DB_PATH}'...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        page_count INTEGER NOT NULL,
        uploaded_at TEXT NOT NULL,
        summary TEXT,
        key_findings TEXT,
        important_dates TEXT
    )
    """)
    
    # 2. Create chat_sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    # 3. Create chat_messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info("SQLite database tables initialized successfully.")

# Document CRUD operations
def add_document(
    doc_id: str,
    filename: str,
    file_path: str,
    file_size: int,
    page_count: int,
    summary: Optional[str] = None,
    key_findings: Optional[List[str]] = None,
    important_dates: Optional[List[str]] = None
) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Serialize lists to JSON strings
        findings_str = json.dumps(key_findings or [])
        dates_str = json.dumps(important_dates or [])
        uploaded_at = datetime.now().isoformat()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO documents (id, filename, file_path, file_size, page_count, uploaded_at, summary, key_findings, important_dates)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, filename, file_path, file_size, page_count, uploaded_at, summary, findings_str, dates_str)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to add document to SQLite: {e}")
        return False

def get_documents() -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, file_size, page_count, uploaded_at FROM documents ORDER BY uploaded_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch documents: {e}")
        return []

def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            doc_dict = dict(row)
            # Deserialize JSON fields
            doc_dict["key_findings"] = json.loads(doc_dict["key_findings"] or "[]")
            doc_dict["important_dates"] = json.loads(doc_dict["important_dates"] or "[]")
            return doc_dict
        return None
    except Exception as e:
        logger.error(f"Failed to fetch document {doc_id}: {e}")
        return None

def delete_document(doc_id: str) -> Optional[str]:
    """
    Deletes document record from SQLite and returns the file path to allow deleting from disk.
    """
    try:
        doc = get_document(doc_id)
        if not doc:
            return None
            
        file_path = doc["file_path"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        
        return file_path
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id} from SQLite: {e}")
        return None

# Session Operations
def create_chat_session(session_id: str, title: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute(
            "INSERT OR IGNORE INTO chat_sessions (id, title, created_at) VALUES (?, ?, ?)",
            (session_id, title, created_at)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to create session {session_id}: {e}")
        return False

def get_chat_sessions() -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch chat sessions: {e}")
        return []

def delete_chat_session(session_id: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to delete session {session_id}: {e}")
        return False

def update_session_title(session_id: str, new_title: str) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (new_title, session_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to update session title {session_id}: {e}")
        return False

# Message Operations
def add_chat_message(
    session_id: str,
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None
) -> bool:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        sources_str = json.dumps(sources or [])
        
        cursor.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, sources, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, sources_str, timestamp)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to add chat message: {e}")
        return False

def get_chat_messages(session_id: str) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            msg = dict(row)
            msg["sources"] = json.loads(msg["sources"] or "[]")
            messages.append(msg)
            
        return messages
    except Exception as e:
        logger.error(f"Failed to fetch chat messages for session {session_id}: {e}")
        return []
