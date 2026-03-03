from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CheckpointRecord:
    job_id: str
    case_id: str
    team_id: str
    status: str
    updated_at: str
    payload: dict[str, Any]


class TeamCheckpointStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS team_checkpoints (
                job_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                team_id TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def upsert(
        self,
        *,
        job_id: str,
        case_id: str,
        team_id: str,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        updated_at = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload, ensure_ascii=False)
        self._conn.execute(
            """
            INSERT INTO team_checkpoints (
                job_id,
                case_id,
                team_id,
                status,
                updated_at,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id)
            DO UPDATE SET
                case_id = excluded.case_id,
                team_id = excluded.team_id,
                status = excluded.status,
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
            """,
            (job_id, case_id, team_id, status, updated_at, payload_json),
        )
        self._conn.commit()

    def get(self, job_id: str) -> CheckpointRecord | None:
        row = self._conn.execute(
            "SELECT * FROM team_checkpoints WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return CheckpointRecord(
            job_id=str(row["job_id"]),
            case_id=str(row["case_id"]),
            team_id=str(row["team_id"]),
            status=str(row["status"]),
            updated_at=str(row["updated_at"]),
            payload=json.loads(str(row["payload_json"])),
        )

    def close(self) -> None:
        self._conn.close()
