from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from binliquid.team.models import (
    AuditEnvelope,
    AuditIntegrity,
    HandoffRecord,
    JobRun,
    TaskRun,
    TeamEvent,
)


@dataclass(slots=True)
class TeamArtifactPaths:
    root_dir: Path
    job_dir: Path
    status_path: Path
    events_path: Path
    tasks_path: Path
    handoffs_path: Path
    envelope_path: Path


def ensure_team_artifact_paths(
    *,
    job_id: str,
    root_dir: str | Path = ".binliquid/team/jobs",
) -> TeamArtifactPaths:
    base = Path(root_dir)
    job_dir = base / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return TeamArtifactPaths(
        root_dir=base,
        job_dir=job_dir,
        status_path=job_dir / "status.json",
        events_path=job_dir / "events.jsonl",
        tasks_path=job_dir / "tasks.json",
        handoffs_path=job_dir / "handoffs.json",
        envelope_path=job_dir / "audit_envelope.json",
    )


def write_event(paths: TeamArtifactPaths, event: TeamEvent) -> None:
    with paths.events_path.open("a", encoding="utf-8") as file_obj:
        file_obj.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")


def write_status(paths: TeamArtifactPaths, payload: dict[str, Any]) -> None:
    paths.status_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_task_runs(paths: TeamArtifactPaths, tasks: list[TaskRun]) -> None:
    payload = {
        "generated_at": _now_iso(),
        "tasks": [item.model_dump(mode="json") for item in tasks],
    }
    paths.tasks_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_handoffs(paths: TeamArtifactPaths, handoffs: list[HandoffRecord]) -> None:
    payload = {
        "generated_at": _now_iso(),
        "handoffs": [item.model_dump(mode="json") for item in handoffs],
    }
    paths.handoffs_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_audit_envelope(
    *,
    paths: TeamArtifactPaths,
    job: JobRun,
    tasks: list[TaskRun],
    events: list[TeamEvent],
    handoffs: list[HandoffRecord],
    policy_bundle_id: str,
    policy_bundle_hash: str,
    runtime_config_hash: str,
) -> str:
    started_at = min((item.timestamp for item in events), default=job.created_at)
    finished_at = max(
        (item.timestamp for item in events),
        default=job.finished_at or datetime.now(UTC),
    )

    decision_chain = []
    approvals = []
    tool_calls = []
    for event in events:
        if event.event in {
            "task_created",
            "task_assigned",
            "handoff",
            "approval_requested",
            "approval_resolved",
            "memory_write_attempt",
            "memory_write_blocked",
            "task_retry",
            "team_final",
        }:
            decision_chain.append(
                {
                    "timestamp": event.timestamp.isoformat(),
                    "event": event.event,
                    "task_id": event.task_id,
                    "reason_code": event.data.get("reason_code"),
                    "data": event.data,
                }
            )
        if event.event in {"approval_requested", "approval_resolved"}:
            approvals.append(
                {
                    "timestamp": event.timestamp.isoformat(),
                    "task_id": event.task_id,
                    "approval_id": event.data.get("approval_id"),
                    "status": event.data.get("status"),
                }
            )
        if event.event == "tool_call":
            tool_calls.append(event.data)

    handoff_payload = [item.model_dump(mode="json") for item in handoffs]
    redaction_report = {
        "handoff_redacted_count": sum(1 for item in handoffs if item.redaction_applied),
        "task_count": len(tasks),
    }

    prev_hash = _read_prev_chain_hash(paths.root_dir)
    envelope_wo_integrity = {
        "envelope_version": "1",
        "job_id": job.job_id,
        "case_id": job.case_id,
        "team_id": job.team_id,
        "policy_bundle_id": policy_bundle_id,
        "policy_bundle_hash": policy_bundle_hash,
        "runtime_config_hash": runtime_config_hash,
        "started_at": started_at,
        "finished_at": finished_at,
        "decision_chain": decision_chain,
        "approvals": approvals,
        "tool_calls": tool_calls,
        "handoffs": handoff_payload,
        "redaction_report": redaction_report,
    }
    current_hash = _sha256_payload(envelope_wo_integrity, prev_hash)
    signature = _sign_hash_if_configured(current_hash)
    envelope = AuditEnvelope(
        envelope_version="1",
        job_id=job.job_id,
        case_id=job.case_id,
        team_id=job.team_id,
        policy_bundle_id=policy_bundle_id,
        policy_bundle_hash=policy_bundle_hash,
        runtime_config_hash=runtime_config_hash,
        started_at=started_at,
        finished_at=finished_at,
        decision_chain=decision_chain,
        approvals=approvals,
        tool_calls=tool_calls,
        handoffs=handoff_payload,
        redaction_report=redaction_report,
        integrity=AuditIntegrity(prev_hash=prev_hash, hash=current_hash, signature=signature),
    )
    paths.envelope_path.write_text(
        json.dumps(envelope.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_chain_hash(paths.root_dir, current_hash)
    return str(paths.envelope_path)


def _sha256_payload(payload: dict[str, Any], prev_hash: str | None) -> str:
    body = {
        "prev_hash": prev_hash,
        "payload": payload,
    }
    raw = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _chain_head_path(root_dir: Path) -> Path:
    chain_dir = root_dir.parent
    chain_dir.mkdir(parents=True, exist_ok=True)
    return chain_dir / "chain_head.txt"


def _read_prev_chain_hash(root_dir: Path) -> str | None:
    path = _chain_head_path(root_dir)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def _write_chain_hash(root_dir: Path, value: str) -> None:
    _chain_head_path(root_dir).write_text(value, encoding="utf-8")


def _sign_hash_if_configured(hash_value: str) -> str | None:
    key = os.getenv("BINLIQUID_AUDIT_SIGNING_KEY", "").strip()
    if not key:
        return None
    digest = hmac.new(
        key.encode("utf-8"),
        hash_value.encode("utf-8"),
        hashlib.sha256,
    )
    return digest.hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
