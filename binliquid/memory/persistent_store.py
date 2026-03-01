from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MemoryRecord:
    id: int
    session_id: str
    task_type: str
    content: str
    content_hash: str
    salience: float
    created_at: str
    expires_at: str | None
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
                content_hash TEXT NOT NULL,
                salience REAL NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                expires_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_memories_task_type ON memories(task_type);
            CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id);
            """
        )

        # Backward-compatible migration for earlier MVP schemas.
        existing_cols = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(memories)").fetchall()
        }
        if "content_hash" not in existing_cols:
            self._conn.execute("ALTER TABLE memories ADD COLUMN content_hash TEXT DEFAULT ''")
            self._conn.execute(
                "UPDATE memories "
                "SET content_hash = lower(hex(randomblob(16))) "
                "WHERE content_hash = ''"
            )
        if "expires_at" not in existing_cols:
            self._conn.execute("ALTER TABLE memories ADD COLUMN expires_at TEXT")

        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(content_hash)")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at)"
        )

        self._conn.commit()

    def write(
        self,
        session_id: str,
        task_type: str,
        content: str,
        salience: float,
        metadata: dict[str, Any] | None = None,
        ttl_days: int | None = 30,
    ) -> int:
        content_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
        now = _utc_now_iso()
        expires_at = _expires_at_iso(ttl_days)
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)

        existing = self._conn.execute(
            """
            SELECT id FROM memories
            WHERE content_hash = ?
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (content_hash, now),
        ).fetchone()

        if existing is not None:
            record_id = int(existing["id"])
            self._conn.execute(
                """
                UPDATE memories
                SET session_id = ?,
                    task_type = ?,
                    content = ?,
                    salience = CASE WHEN salience > ? THEN salience ELSE ? END,
                    metadata_json = ?,
                    created_at = ?,
                    expires_at = ?,
                    content_hash = ?
                WHERE id = ?
                """,
                (
                    session_id,
                    task_type,
                    content,
                    salience,
                    salience,
                    meta_json,
                    now,
                    expires_at,
                    content_hash,
                    record_id,
                ),
            )
            self._conn.commit()
            return record_id

        cursor = self._conn.execute(
            """
            INSERT INTO memories (
                session_id,
                task_type,
                content,
                content_hash,
                salience,
                metadata_json,
                created_at,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, task_type, content, content_hash, salience, meta_json, now, expires_at),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def recent(self, limit: int = 10, include_expired: bool = False) -> list[MemoryRecord]:
        if include_expired:
            query = """
                SELECT id, session_id, task_type, content, content_hash, salience,
                       metadata_json, created_at, expires_at
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            """
            params: tuple[object, ...] = (limit,)
        else:
            query = """
                SELECT id, session_id, task_type, content, content_hash, salience,
                       metadata_json, created_at, expires_at
                FROM memories
                WHERE (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT ?
            """
            params = (self._now_iso(), limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def search(
        self,
        keyword: str,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[MemoryRecord]:
        if include_expired:
            query = """
                SELECT id, session_id, task_type, content, content_hash, salience,
                       metadata_json, created_at, expires_at
                FROM memories
                WHERE content LIKE ?
                ORDER BY salience DESC, created_at DESC
                LIMIT ?
            """
            params = (f"%{keyword}%", limit)
        else:
            query = """
                SELECT id, session_id, task_type, content, content_hash, salience,
                       metadata_json, created_at, expires_at
                FROM memories
                WHERE content LIKE ?
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY salience DESC, created_at DESC
                LIMIT ?
            """
            params = (f"%{keyword}%", self._now_iso(), limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def prune_to_limit(self, max_rows: int) -> int:
        if max_rows <= 0:
            return 0

        now = self._now_iso()
        expired_deleted = self._conn.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        ).rowcount

        total = self.count(include_expired=False)
        if total <= max_rows:
            self._conn.commit()
            return int(expired_deleted)

        to_delete = total - max_rows
        self._conn.execute(
            """
            DELETE FROM memories
            WHERE id IN (
                SELECT id FROM memories
                WHERE (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at ASC
                LIMIT ?
            )
            """,
            (now, to_delete),
        )
        self._conn.commit()
        return int(expired_deleted + to_delete)

    def count(self, include_expired: bool = False) -> int:
        if include_expired:
            row = self._conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM memories WHERE (expires_at IS NULL OR expires_at > ?)",
                (self._now_iso(),),
            ).fetchone()
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
            content_hash=str(row["content_hash"]),
            salience=float(row["salience"]),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]) if row["expires_at"] is not None else None,
            metadata=json.loads(str(row["metadata_json"] or "{}")),
        )

    @staticmethod
    def _now_iso() -> str:
        return _utc_now_iso()


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _expires_at_iso(ttl_days: int | None) -> str | None:
    if ttl_days is None or ttl_days <= 0:
        return None
    expires = datetime.now(UTC) + timedelta(days=ttl_days)
    return expires.isoformat(timespec="milliseconds").replace("+00:00", "Z")
