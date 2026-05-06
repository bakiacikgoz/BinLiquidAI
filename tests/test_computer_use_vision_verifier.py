from __future__ import annotations

from binliquid.computer_use.models import RiskClass
from binliquid.computer_use.vision_runtime.models import (
    InputActionType,
    NormalizedBBox,
    SurfaceKind,
    VisionAction,
    VisionObservation,
)
from binliquid.computer_use.vision_runtime.verifier import ConservativeVisionStepVerifier


def _observation(hash_char: str) -> VisionObservation:
    return VisionObservation(
        screenshot_hash=hash_char * 64,
        captured_at="2026-05-05T00:00:00+00:00",
        platform="macos",
        surface_kind=SurfaceKind.BROWSER,
        confidence=0.92,
    )


def _action(action_type: InputActionType) -> VisionAction:
    return VisionAction(
        action_id=f"act-{action_type.value}",
        action_type=action_type,
        target_bbox=NormalizedBBox(x=0.1, y=0.1, w=0.2, h=0.2),
        rationale="Exercise verifier behavior.",
        expected_effect="The local fixture advances.",
        risk_class=RiskClass.LOW if action_type == InputActionType.WAIT else RiskClass.MEDIUM,
        requires_approval=False,
        confidence=0.9,
    )


def test_conservative_verifier_accepts_wait_without_hash_change() -> None:
    verifier = ConservativeVisionStepVerifier()

    result = verifier.verify(
        before=_observation("a"),
        action=_action(InputActionType.WAIT),
        after=_observation("a"),
    )

    assert result.verified is True
    assert result.confidence == 0.75


def test_conservative_verifier_rejects_click_without_hash_change() -> None:
    verifier = ConservativeVisionStepVerifier()

    result = verifier.verify(
        before=_observation("a"),
        action=_action(InputActionType.CLICK),
        after=_observation("a"),
    )

    assert result.verified is False
    assert result.confidence == 0.2


def test_conservative_verifier_accepts_click_with_hash_change() -> None:
    verifier = ConservativeVisionStepVerifier()

    result = verifier.verify(
        before=_observation("a"),
        action=_action(InputActionType.CLICK),
        after=_observation("b"),
    )

    assert result.verified is True
    assert result.confidence == 0.9
