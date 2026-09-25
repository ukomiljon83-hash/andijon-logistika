import sqlite3
from contextlib import contextmanager

DB_PATH = "logistics.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            client_name TEXT,
            phone TEXT,
            dropoff_address TEXT,
            comment TEXT,
            price INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Yangi',
            courier_id INTEGER,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY,
            name TEXT,
            phone TEXT,
            active INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Offline',
            lat REAL,
            lon REAL,
            updated_at TEXT
        )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
