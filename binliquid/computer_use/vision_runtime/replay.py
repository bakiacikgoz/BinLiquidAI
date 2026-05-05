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
    verification = verify_replay(job_dir)
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
        "verified": verification["verified"],
        "checks": verification["checks"],
        "errors": verification["errors"],
    }


def verify_replay(job_dir: Path) -> dict[str, Any]:
    events_path = job_dir / "events.jsonl"
    envelope_path = job_dir / "audit_envelope.json"
    errors: list[str] = []
    checks = {
        "hash_chain_verified": False,
        "step_index_monotonic": False,
        "approval_required_not_executed": False,
        "screenshot_hash_format": False,
        "raw_screenshot_policy": False,
    }
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    previous = ""
    hash_ok = True
    for event in events:
        expected = _event_hash({key: value for key, value in event.items() if key != "hash"})
        if event.get("prev_hash") != previous or event.get("hash") != expected:
            hash_ok = False
            errors.append("hash_chain verification failed")
            break
        previous = str(event.get("hash") or "")
    checks["hash_chain_verified"] = hash_ok

    indices = [int(event.get("step_index", -1)) for event in events]
    checks["step_index_monotonic"] = indices == sorted(indices) and all(
        index >= 0 for index in indices
    )
    if not checks["step_index_monotonic"]:
        errors.append("step_index monotonicity failed")

    approval_ok = True
    hash_format_ok = True
    for event in events:
        payload = event.get("payload", {})
        if (
            payload.get("execution_status") == "executed"
            and payload.get("policy_decision", {}).get("requires_approval") is True
        ):
            approval_ok = False
        for key in ("before_hash", "after_hash"):
            value = payload.get(key)
            if value is None:
                continue
            if not (isinstance(value, str) and len(value) == 64 and _is_hex(value)):
                hash_format_ok = False
    checks["approval_required_not_executed"] = approval_ok
    checks["screenshot_hash_format"] = hash_format_ok
    if not approval_ok:
        errors.append("approval-required action executed without replay-safe boundary")
    if not hash_format_ok:
        errors.append("screenshot hash format invalid")

    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    raw_count = envelope.get("redaction_report", {}).get("raw_screenshot_persisted_count", 0)
    checks["raw_screenshot_policy"] = raw_count == 0
    if raw_count != 0:
        errors.append("raw screenshot persistence violates default replay policy")

    return {
        "artifact_version": "computer_use_vision_replay_verification/v1",
        "verified": all(checks.values()),
        "checks": checks,
        "errors": errors,
    }


def _event_hash(event: dict[str, Any]) -> str:
    import hashlib

    payload = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_hex(value: str) -> bool:
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
