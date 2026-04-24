"""SQLite-backed conversation memory for RAG follow-ups."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Stores conversation history in SQLite for multi-turn RAG queries."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist, then migrate any new columns.

        We use a migrate-lite pattern so existing sandboxes / prod DBs keep
        working without a separate Alembic step: check `PRAGMA table_info`
        and `ALTER TABLE ... ADD COLUMN` when a column is missing.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources TEXT DEFAULT '[]',
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, timestamp)
            """)

            # Phase 1 — persona column on messages. Idempotent.
            existing_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(messages)")
            }
            if "persona" not in existing_cols:
                conn.execute("ALTER TABLE messages ADD COLUMN persona TEXT")

    def create_conversation(self, title: str = "") -> str:
        """Create a new conversation and return its ID."""
        conv_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (conv_id, title, now, now),
            )
        return conv_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list = None,
        persona: Optional[str] = None,
    ) -> None:
        """Add a message to a conversation."""
        now = datetime.utcnow().isoformat()
        sources_json = json.dumps(sources or [])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content, sources, persona, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conversation_id, role, content, sources_json, persona, now),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ?, title = CASE WHEN title = '' THEN ? ELSE title END WHERE id = ?",
                (now, content[:100] if role == "user" else "", conversation_id),
            )

    def get_history(self, conversation_id: str, last_n: int = 3) -> List[dict]:
        """Get the last N message exchanges for a conversation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT role, content, sources, persona, timestamp FROM messages "
                "WHERE conversation_id = ? ORDER BY timestamp DESC LIMIT ?",
                (conversation_id, last_n * 2),  # *2 for user+assistant pairs
            ).fetchall()
        # Reverse to chronological order
        return [
            {
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources"]),
                "persona": row["persona"] if "persona" in row.keys() else None,
                "timestamp": row["timestamp"],
            }
            for row in reversed(rows)
        ]

    def list_conversations(self, limit: int = 50) -> List[dict]:
        """List recent conversations."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT c.id, c.title, c.created_at, c.updated_at, "
                "(SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count "
                "FROM conversations c ORDER BY c.updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a conversation and all its messages."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Get conversation metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return dict(row) if row else None
