from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MemoryRecord:
    id: int
    session_id: str
    task_type: str
    content: str
    salience: float
    created_at: str
    metadata: dict[str, Any]


class PersistentMemoryStore:
    """Local SQLite store for long-term memory candidates."""

    def __init__(self, db_path: str | Path = ".binliquid/memory.sqlite3"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                content TEXT NOT NULL,
                salience REAL NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_task_type ON memories(task_type);
            CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);
            """
        )
        self._conn.commit()

    def write(
        self,
        session_id: str,
        task_type: str,
        content: str,
        salience: float,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        cursor = self._conn.execute(
            """
            INSERT INTO memories (session_id, task_type, content, salience, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, task_type, content, salience, meta_json),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def recent(self, limit: int = 10) -> list[MemoryRecord]:
        rows = self._conn.execute(
            """
            SELECT id, session_id, task_type, content, salience, metadata_json, created_at
            FROM memories
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def search(self, keyword: str, limit: int = 10) -> list[MemoryRecord]:
        rows = self._conn.execute(
            """
            SELECT id, session_id, task_type, content, salience, metadata_json, created_at
            FROM memories
            WHERE content LIKE ?
            ORDER BY salience DESC, created_at DESC
            LIMIT ?
            """,
            (f"%{keyword}%", limit),
        ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def prune_to_limit(self, max_rows: int) -> int:
        if max_rows <= 0:
            return 0
        total = self.count()
        if total <= max_rows:
            return 0

        to_delete = total - max_rows
        self._conn.execute(
            """
            DELETE FROM memories
            WHERE id IN (
                SELECT id FROM memories
                ORDER BY created_at ASC
                LIMIT ?
            )
            """,
            (to_delete,),
        )
        self._conn.commit()
        return to_delete

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        return int(row["c"]) if row is not None else 0

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=int(row["id"]),
            session_id=str(row["session_id"]),
            task_type=str(row["task_type"]),
            content=str(row["content"]),
            salience=float(row["salience"]),
            created_at=str(row["created_at"]),
            metadata=json.loads(str(row["metadata_json"] or "{}")),
        )
