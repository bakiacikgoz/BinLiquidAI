from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from binliquid.computer_use.models import RiskClass
from binliquid.computer_use.vision_runtime.drivers.macos import (
    DisplayBounds,
    MacOSInputExecutor,
    MacOSScreenCaptureProvider,
    MacOSVisionReadiness,
    normalized_bbox_center_to_pixel,
)
from binliquid.computer_use.vision_runtime.errors import VisionRuntimeError
from binliquid.computer_use.vision_runtime.models import (
    InputActionType,
    NormalizedBBox,
    VisionAction,
)
from binliquid.runtime.config import ComputerUseRuntimeConfig
from binliquid.runtime.platform import PlatformInfo


def _action(action_type: InputActionType = InputActionType.CLICK) -> VisionAction:
    return VisionAction(
        action_id="act-1",
        action_type=action_type,
        target_bbox=NormalizedBBox(x=0.25, y=0.25, w=0.5, h=0.5),
        text="safe",
        hotkey=["cmd", "q"] if action_type == InputActionType.HOTKEY else [],
        rationale="Exercise macOS driver policy.",
        expected_effect="A safe fixture changes state.",
        risk_class=RiskClass.LOW,
        requires_approval=False,
        confidence=0.95,
    )


def test_macos_readiness_blocks_non_macos_live_request() -> None:
    report = MacOSVisionReadiness(
        ComputerUseRuntimeConfig(
            runtime_mode="vision_first",
            vision_enabled=True,
            vision_provider="ollama",
            vision_model="llava",
            macos_live_enabled=True,
        )
    ).evaluate(
        platform_info=PlatformInfo(system="Windows", label="windows", machine="x64", release="11")
    )

    assert report["live_execution_allowed"] is False
    assert report["checks"][0]["reason_code"] == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"


def test_screencapture_hashes_bytes_and_deletes_temp_by_default(tmp_path: Path) -> None:
    captured_paths: list[Path] = []

    def fake_runner(args, capture_output, text, check):  # noqa: ANN001
        del capture_output, text, check
        capture_path = Path(args[-1])
        captured_paths.append(capture_path)
        capture_path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        return SimpleNamespace(returncode=0, stderr="")

    provider = MacOSScreenCaptureProvider(
        config=ComputerUseRuntimeConfig(),
        job_dir=tmp_path / "job",
        raw_screenshot_opt_in=False,
        runner=fake_runner,
        now=lambda: "2026-05-05T00:00:00+00:00",
    )

    observation = provider.capture()

    assert len(observation.screenshot_hash) == 64
    assert observation.raw_screenshot_path is None
    assert captured_paths and not captured_paths[0].exists()


def test_capture_backend_unavailable_fails_closed(tmp_path: Path) -> None:
    def missing_runner(args, capture_output, text, check):  # noqa: ANN001
        del args, capture_output, text, check
        raise FileNotFoundError("screencapture")

    provider = MacOSScreenCaptureProvider(
        config=ComputerUseRuntimeConfig(),
        job_dir=tmp_path / "job",
        runner=missing_runner,
    )

    try:
        provider.capture()
    except VisionRuntimeError as exc:
        assert exc.reason_code == "MACOS_CAPTURE_BACKEND_UNAVAILABLE"
    else:  # pragma: no cover
        raise AssertionError("expected fail-closed capture error")


def test_normalized_bbox_to_pixel_clamps_to_display_bounds() -> None:
    point = normalized_bbox_center_to_pixel(
        NormalizedBBox(x=0.95, y=0.95, w=0.2, h=0.2),
        DisplayBounds(width=100, height=50),
    )

    assert point == (99, 49)


def test_macos_input_executor_requires_quartz_backend() -> None:
    executor = MacOSInputExecutor(
        config=ComputerUseRuntimeConfig(macos_input_backend="quartz"),
        quartz_backend=None,
    )

    result = executor.execute(_action())

    assert result.status == "failed"
    assert result.details["reason_code"] == "MACOS_INPUT_BACKEND_UNAVAILABLE"


def test_macos_input_executor_blocks_risky_hotkey_even_with_backend() -> None:
    executor = MacOSInputExecutor(
        config=ComputerUseRuntimeConfig(macos_input_backend="quartz"),
        quartz_backend=SimpleNamespace(move_mouse=lambda *_: None, click=lambda *_: None),
    )

    result = executor.execute(_action(InputActionType.HOTKEY))

    assert result.status == "blocked"
    assert result.details["reason_code"] == "COMPUTER_USE_APPROVAL_REQUIRED"
