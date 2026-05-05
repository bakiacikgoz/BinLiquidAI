from __future__ import annotations

import json
from pathlib import Path

from binliquid.computer_use.models import RiskClass
from binliquid.computer_use.vision_runtime.models import (
    InputActionType,
    VisionAction,
    VisionPolicyDecision,
    VisionStepResult,
)
from binliquid.computer_use.vision_runtime.recorder import RedactedVisionAuditRecorder
from binliquid.computer_use.vision_runtime.replay import load_replay_summary


def _step(step_index: int) -> VisionStepResult:
    return VisionStepResult(
        step_index=step_index,
        before_hash="e" * 64,
        action=VisionAction(
            action_id=f"act-{step_index}",
            action_type=InputActionType.WAIT,
            rationale="Wait for stable UI.",
            expected_effect="UI remains stable.",
            risk_class=RiskClass.LOW,
            requires_approval=False,
            confidence=0.9,
        ),
        policy_decision=VisionPolicyDecision(
            allowed=True,
            requires_approval=False,
            denied=False,
            reason_code="POLICY_ALLOW",
            risk_reasons=[],
            policy_hash="policy",
        ),
        execution_status="executed",
        after_hash="f" * 64,
    )


def test_recorder_writes_redacted_hash_chain_and_replay_summary(tmp_path: Path) -> None:
    recorder = RedactedVisionAuditRecorder(
        job_id="job-replay",
        job_dir=tmp_path / "job-replay",
        runtime_config_hash="runtime-hash",
        policy_hash="policy-hash",
    )

    recorder.record_step(_step(0))
    envelope = recorder.finalize("completed")

    events_path = tmp_path / "job-replay" / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]

    assert envelope["integrity"]["hash_chain_verified"] is True
    assert events[0]["prev_hash"] == ""
    assert events[0]["hash"]
    assert "raw_screenshot_path" not in json.dumps(events)

    replay = load_replay_summary(tmp_path / "job-replay")

    assert replay["job_id"] == "job-replay"
    assert replay["status"] == "completed"
    assert replay["event_count"] == 1
    assert replay["redacted"] is True
