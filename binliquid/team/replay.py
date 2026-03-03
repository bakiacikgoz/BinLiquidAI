from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _job_dir(job_id: str, root_dir: str | Path = ".binliquid/team/jobs") -> Path:
    return Path(root_dir) / job_id


def load_job_status(job_id: str, root_dir: str | Path = ".binliquid/team/jobs") -> dict[str, Any]:
    path = _job_dir(job_id, root_dir) / "status.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_events(job_id: str, root_dir: str | Path = ".binliquid/team/jobs") -> list[dict[str, Any]]:
    path = _job_dir(job_id, root_dir) / "events.jsonl"
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def load_audit_envelope(
    job_id: str,
    root_dir: str | Path = ".binliquid/team/jobs",
) -> dict[str, Any]:
    path = _job_dir(job_id, root_dir) / "audit_envelope.json"
    return json.loads(path.read_text(encoding="utf-8"))


def replay_job(job_id: str, root_dir: str | Path = ".binliquid/team/jobs") -> dict[str, Any]:
    status = load_job_status(job_id, root_dir)
    events = load_events(job_id, root_dir)
    envelope = load_audit_envelope(job_id, root_dir)

    task_events = [
        item
        for item in events
        if item.get("event") in {"task_created", "task_assigned"}
    ]
    handoff_events = [item for item in events if item.get("event") == "handoff"]
    approval_events = [
        item
        for item in events
        if item.get("event") in {"approval_requested", "approval_resolved"}
    ]

    return {
        "job_id": job_id,
        "status": status.get("job", {}).get("status"),
        "team_id": status.get("job", {}).get("team_id"),
        "case_id": status.get("job", {}).get("case_id"),
        "final_output": status.get("job", {}).get("final_output"),
        "event_count": len(events),
        "task_event_count": len(task_events),
        "handoff_event_count": len(handoff_events),
        "approval_event_count": len(approval_events),
        "decision_count": len(envelope.get("decision_chain", [])),
        "integrity": envelope.get("integrity", {}),
    }
