from sqlmodel import SQLModel, create_engine
from pathlib import Path
import os
import sqlite3

DB_PATH = os.getenv("GRADER_DB_PATH") or str(Path(__file__).resolve().parent.parent / "grader.db")
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict):
    cur = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    for name, ddl in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def migrate_sqlite_if_needed():
    conn = sqlite3.connect(DB_PATH)
    try:
        # submission columns
        _ensure_columns(conn, "submission", {
            "user_id": "INTEGER",
            "user_name": "TEXT",
            "score": "INTEGER DEFAULT 0",
            "max_score": "INTEGER DEFAULT 100",
            "passed_tests": "INTEGER DEFAULT 0",
            "total_tests": "INTEGER DEFAULT 0",
            "penalty": "INTEGER DEFAULT 0",
        })
        # problem columns
        _ensure_columns(conn, "problem", {
            "description": "TEXT",
            "pdf_path": "TEXT",
            "max_score": "INTEGER DEFAULT 100",
            "testcase_count": "INTEGER DEFAULT 0",
        })
        # userstats table (create if not exists)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS userstats (
            id INTEGER PRIMARY KEY,
            user_name TEXT UNIQUE,
            total_score INTEGER DEFAULT 0,
            total_submissions INTEGER DEFAULT 0,
            problems_solved INTEGER DEFAULT 0,
            last_activity TIMESTAMP
        )
        """)
        conn.commit()
    finally:
        conn.close()


def init_db():
    from app import models  # ensure models are imported
    SQLModel.metadata.create_all(engine)
    migrate_sqlite_if_needed()