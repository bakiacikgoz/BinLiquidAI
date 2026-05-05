from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_replay_summary(job_dir: Path) -> dict[str, Any]:
    envelope_path = job_dir / "audit_envelope.json"
    events_path = job_dir / "events.jsonl"
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {
        "artifact_version": "computer_use_vision_replay/v1",
        "job_id": envelope["job_id"],
        "status": envelope["status"],
        "event_count": len(events),
        "redacted": envelope.get("redaction_report", {}).get("redacted") is True,
        "hash_chain_verified": envelope.get("integrity", {}).get("hash_chain_verified") is True,
        "steps": [
            {
                "step_index": event.get("step_index"),
                "event_type": event.get("event_type"),
                "action_type": event.get("payload", {}).get("action", {}).get("action_type"),
                "execution_status": event.get("payload", {}).get("execution_status"),
                "before_hash": event.get("payload", {}).get("before_hash"),
                "after_hash": event.get("payload", {}).get("after_hash"),
            }
            for event in events
        ],
    }
