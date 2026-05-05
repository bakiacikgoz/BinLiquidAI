from __future__ import annotations

from datetime import UTC, datetime, timedelta

from binliquid.computer_use.models import RiskClass
from binliquid.computer_use.vision_runtime.approval import validate_approval_snapshot
from binliquid.computer_use.vision_runtime.models import (
    InputActionType,
    NormalizedBBox,
    SurfaceKind,
    VisionAction,
    VisionObservation,
)
from binliquid.computer_use.vision_runtime.runtime import build_approval_snapshot
from binliquid.runtime.config import ComputerUseRuntimeConfig


def _observation() -> VisionObservation:
    return VisionObservation(
        screenshot_hash="f" * 64,
        captured_at="2026-05-05T00:00:00+00:00",
        platform="macos",
        active_app="Safari",
        active_window_title="Fixture",
        surface_kind=SurfaceKind.BROWSER,
        confidence=0.92,
    )


def _action() -> VisionAction:
    return VisionAction(
        action_id="act-approval",
        action_type=InputActionType.CLICK,
        target_bbox=NormalizedBBox(x=0.1, y=0.2, w=0.2, h=0.1),
        rationale="Click safe fixture button.",
        expected_effect="Fixture state changes.",
        risk_class=RiskClass.MEDIUM,
        requires_approval=True,
        confidence=0.91,
    )


def test_approval_snapshot_contains_hashes_and_surface_identity() -> None:
    snapshot = build_approval_snapshot(
        job_id="job-1",
        step_index=1,
        objective="Click safe fixture",
        observation=_observation(),
        action=_action(),
        policy_hash="policy",
        risk_reasons=["step_approval_mode"],
        max_age_ms=10000,
        created_at="2026-05-05T00:00:00+00:00",
    )

    assert snapshot["objective_hash"]
    assert snapshot["action_hash"]
    assert snapshot["active_app"] == "Safari"
    assert snapshot["raw_screenshot_path"] is None


def test_stale_approval_snapshot_blocks_execution() -> None:
    snapshot = build_approval_snapshot(
        job_id="job-1",
        step_index=1,
        objective="Click safe fixture",
        observation=_observation(),
        action=_action(),
        policy_hash="policy",
        risk_reasons=["step_approval_mode"],
        max_age_ms=1000,
        created_at=(datetime.now(UTC) - timedelta(seconds=5)).isoformat(),
    )

    result = validate_approval_snapshot(
        snapshot=snapshot,
        current_observation=_observation(),
        action=_action(),
        policy_hash="policy",
        config=ComputerUseRuntimeConfig(),
        now=datetime.now(UTC),
    )

    assert result.allowed is False
    assert result.reason_code == "COMPUTER_USE_STALE_APPROVAL_SNAPSHOT"
