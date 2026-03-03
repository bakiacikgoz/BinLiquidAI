from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from binliquid.governance.models import ApprovalStatus, ApprovalTicket, ExecutionStatus


@dataclass(slots=True)
class ApprovalDecisionResult:
    ticket: ApprovalTicket | None
    error_code: str | None = None


class ApprovalStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    run_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    snapshot_hash TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    actor TEXT,
                    decision_reason TEXT,
                    execution_status TEXT NOT NULL,
                    executed_at TEXT,
                    execution_error_code TEXT,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    decided_at TEXT
                )
                """
            )

    def create_ticket(
        self,
        *,
        run_id: str,
        request_hash: str,
        snapshot_hash: str,
        snapshot: dict[str, Any],
        ttl_seconds: int,
        idempotency_key: str,
    ) -> ApprovalTicket:
        now = datetime.now(UTC)
        ticket = ApprovalTicket(
            version=0,
            approval_id=str(uuid4()),
            run_id=run_id,
            status=ApprovalStatus.PENDING,
            request_hash=request_hash,
            snapshot_hash=snapshot_hash,
            snapshot=snapshot,
            expires_at=now + timedelta(seconds=ttl_seconds),
            execution_status=ExecutionStatus.NOT_EXECUTED,
            idempotency_key=idempotency_key,
            created_at=now,
        )
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO approvals (
                    approval_id, version, run_id, status, request_hash, snapshot_hash,
                    snapshot_json, expires_at, actor, decision_reason, execution_status,
                    executed_at, execution_error_code, idempotency_key, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.approval_id,
                    ticket.version,
                    ticket.run_id,
                    ticket.status.value,
                    ticket.request_hash,
                    ticket.snapshot_hash,
                    json.dumps(ticket.snapshot, ensure_ascii=False, sort_keys=True),
                    ticket.expires_at.isoformat(),
                    ticket.actor,
                    ticket.decision_reason,
                    ticket.execution_status.value,
                    ticket.executed_at.isoformat() if ticket.executed_at else None,
                    ticket.execution_error_code,
                    ticket.idempotency_key,
                    ticket.created_at.isoformat(),
                    ticket.decided_at.isoformat() if ticket.decided_at else None,
                ),
            )
        return ticket

    def list_pending(self) -> list[ApprovalTicket]:
        self.expire_pending()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE status = ? ORDER BY created_at ASC",
                (ApprovalStatus.PENDING.value,),
            ).fetchall()
        return [self._row_to_ticket(row) for row in rows]

    def get(self, approval_id: str) -> ApprovalTicket | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_ticket(row)

    def expire_pending(self) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE approvals
                SET status = ?, version = version + 1
                WHERE status IN (?, ?) AND expires_at <= ?
                """,
                (
                    ApprovalStatus.EXPIRED.value,
                    ApprovalStatus.PENDING.value,
                    ApprovalStatus.APPROVED.value,
                    now_iso,
                ),
            )

    def decide(
        self,
        *,
        approval_id: str,
        approve: bool,
        actor: str,
        reason: str | None,
    ) -> ApprovalDecisionResult:
        self.expire_pending()
        ticket = self.get(approval_id)
        if ticket is None:
            return ApprovalDecisionResult(ticket=None, error_code="APPROVAL_NOT_FOUND")
        if ticket.status != ApprovalStatus.PENDING:
            return ApprovalDecisionResult(ticket=ticket, error_code="APPROVAL_CONFLICT")
        now = datetime.now(UTC)
        new_status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED

        with self._conn() as conn:
            updated = conn.execute(
                """
                UPDATE approvals
                SET status = ?, actor = ?, decision_reason = ?, decided_at = ?,
                    version = version + 1
                WHERE approval_id = ? AND version = ? AND status = ?
                """,
                (
                    new_status.value,
                    actor,
                    reason,
                    now.isoformat(),
                    approval_id,
                    ticket.version,
                    ApprovalStatus.PENDING.value,
                ),
            ).rowcount
        if updated == 0:
            return ApprovalDecisionResult(
                ticket=self.get(approval_id),
                error_code="APPROVAL_CONFLICT",
            )
        return ApprovalDecisionResult(ticket=self.get(approval_id), error_code=None)

    def mark_executed(self, *, approval_id: str) -> ApprovalDecisionResult:
        self.expire_pending()
        ticket = self.get(approval_id)
        if ticket is None:
            return ApprovalDecisionResult(ticket=None, error_code="APPROVAL_NOT_FOUND")
        if ticket.status != ApprovalStatus.APPROVED:
            return ApprovalDecisionResult(ticket=ticket, error_code="APPROVAL_CONFLICT")
        if ticket.execution_status == ExecutionStatus.EXECUTED:
            return ApprovalDecisionResult(ticket=ticket, error_code="REPLAY_BLOCKED")

        now = datetime.now(UTC)
        with self._conn() as conn:
            updated = conn.execute(
                """
                UPDATE approvals
                SET status = ?, execution_status = ?, executed_at = ?, version = version + 1
                WHERE approval_id = ? AND version = ? AND status = ?
                """,
                (
                    ApprovalStatus.EXECUTED.value,
                    ExecutionStatus.EXECUTED.value,
                    now.isoformat(),
                    approval_id,
                    ticket.version,
                    ApprovalStatus.APPROVED.value,
                ),
            ).rowcount
        if updated == 0:
            return ApprovalDecisionResult(
                ticket=self.get(approval_id),
                error_code="APPROVAL_CONFLICT",
            )
        return ApprovalDecisionResult(ticket=self.get(approval_id), error_code=None)

    def mark_execution_failed(self, *, approval_id: str, error_code: str) -> ApprovalDecisionResult:
        ticket = self.get(approval_id)
        if ticket is None:
            return ApprovalDecisionResult(ticket=None, error_code="APPROVAL_NOT_FOUND")
        now = datetime.now(UTC)
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE approvals
                SET status = ?, execution_status = ?, executed_at = ?,
                    execution_error_code = ?, version = version + 1
                WHERE approval_id = ?
                """,
                (
                    ApprovalStatus.EXECUTION_FAILED.value,
                    ExecutionStatus.EXECUTION_FAILED.value,
                    now.isoformat(),
                    error_code,
                    approval_id,
                ),
            )
        return ApprovalDecisionResult(ticket=self.get(approval_id), error_code=None)

    @staticmethod
    def _row_to_ticket(row: sqlite3.Row) -> ApprovalTicket:
        return ApprovalTicket(
            version=int(row["version"]),
            approval_id=str(row["approval_id"]),
            run_id=str(row["run_id"]),
            status=ApprovalStatus(str(row["status"])),
            request_hash=str(row["request_hash"]),
            snapshot_hash=str(row["snapshot_hash"]),
            snapshot=json.loads(str(row["snapshot_json"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"])),
            actor=str(row["actor"]) if row["actor"] else None,
            decision_reason=str(row["decision_reason"]) if row["decision_reason"] else None,
            execution_status=ExecutionStatus(str(row["execution_status"])),
            executed_at=(
                datetime.fromisoformat(str(row["executed_at"])) if row["executed_at"] else None
            ),
            execution_error_code=(
                str(row["execution_error_code"]) if row["execution_error_code"] else None
            ),
            idempotency_key=str(row["idempotency_key"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            decided_at=(
                datetime.fromisoformat(str(row["decided_at"])) if row["decided_at"] else None
            ),
        )
