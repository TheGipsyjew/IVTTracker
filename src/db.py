import sqlite3
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ivt_tracker.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_hash TEXT UNIQUE NOT NULL,
            author TEXT,
            date TEXT,
            category TEXT,
            content TEXT,
            created_at TEXT,
            classified INTEGER DEFAULT 0,
            classification_json TEXT
        );
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER REFERENCES posts(id),
            type TEXT,
            asset TEXT,
            direction TEXT,
            entry_zone TEXT,
            stop_loss TEXT,
            take_profit TEXT,
            confidence REAL,
            rationale TEXT,
            posted_at TEXT,
            detected_at TEXT
        );
    """)
    conn.commit()
    conn.close()


def post_hash(author: str, content: str) -> str:
    return hashlib.sha256(f"{author.strip()}|||{content.strip()}".encode()).hexdigest()


def store_post(author: str, date: str, category: str, content: str) -> tuple[bool, int | None]:
    """Store a post. Returns (is_new, post_id)."""
    conn = _get_conn()
    ph = post_hash(author, content)
    existing = conn.execute(
        "SELECT id, classified FROM posts WHERE post_hash = ?", (ph,)
    ).fetchone()
    if existing:
        conn.close()
        return False, existing["id"]

    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO posts (post_hash, author, date, category, content, created_at, classified) VALUES (?, ?, ?, ?, ?, ?, 0)",
        (ph, author, date, category, content, now),
    )
    conn.commit()
    post_id = cursor.lastrowid
    conn.close()
    return True, post_id


def update_classification(post_id: int, classification: dict):
    conn = _get_conn()
    conn.execute(
        "UPDATE posts SET classified = 1, classification_json = ? WHERE id = ?",
        (json.dumps(classification, ensure_ascii=False), post_id),
    )
    # If it's a call type, also store in the calls table
    ctype = classification.get("type", "")
    if ctype in ("new_call", "follow_up", "close"):
        conn.execute(
            """INSERT INTO calls (
                post_id, type, asset, direction, entry_zone,
                stop_loss, take_profit, confidence, rationale,
                posted_at, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                post_id,
                ctype,
                classification.get("asset"),
                classification.get("direction"),
                classification.get("entry_zone"),
                classification.get("stop_loss"),
                classification.get("take_profit"),
                classification.get("confidence"),
                classification.get("rationale"),
                None,  # posted_at — would need to parse from text
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    conn.commit()
    conn.close()


def get_unclassified_posts(limit: int = 100):
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, author, date, category, content FROM posts WHERE classified = 0 ORDER BY id ASC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "author": r["author"],
            "date": r["date"],
            "category": r["category"],
            "content": r["content"],
        }
        for r in rows
    ]
