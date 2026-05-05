from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from binliquid.computer_use.vision_runtime.drivers.base import PlatformDriverReadiness
from binliquid.computer_use.vision_runtime.errors import VisionRuntimeError
from binliquid.computer_use.vision_runtime.models import (
    ExecutionResult,
    InputActionType,
    NormalizedBBox,
    VisionAction,
    VisionObservation,
)
from binliquid.computer_use.vision_runtime.platforms import (
    PlatformCapability,
    build_platform_capability,
)
from binliquid.runtime.config import ComputerUseRuntimeConfig
from binliquid.runtime.platform import PlatformInfo, current_platform


@dataclass(frozen=True, slots=True)
class DisplayBounds:
    width: int
    height: int
    origin_x: int = 0
    origin_y: int = 0


def readiness(*, vision_enabled: bool) -> PlatformDriverReadiness:
    return PlatformDriverReadiness(
        platform="macos",
        live_execution_enabled=vision_enabled,
        reason_code=None if vision_enabled else "VISION_RUNTIME_NOT_CONFIGURED",
        summary=(
            "macOS vision-first runtime is configured for supervised execution."
            if vision_enabled
            else "macOS vision-first runtime is scaffolded but no vision provider is configured."
        ),
    )


def readiness_report(
    config: ComputerUseRuntimeConfig,
    *,
    environment: Mapping[str, str] | None = None,
    qualification_report: Mapping[str, Any] | None = None,
    commit: str | None = None,
) -> PlatformCapability:
    return build_platform_capability(
        config,
        platform="macos",
        environment=environment,
        qualification_report=qualification_report,
        commit=commit,
    )


class MacOSVisionReadiness:
    def __init__(self, config: ComputerUseRuntimeConfig) -> None:
        self.config = config

    def evaluate(
        self,
        *,
        platform_info: PlatformInfo | None = None,
        which: Callable[[str], str | None] = shutil.which,
        input_backend_available: bool | None = None,
    ) -> dict[str, Any]:
        platform = platform_info or current_platform()
        checks: list[dict[str, Any]] = []
        if platform.label != "macos":
            reason = (
                "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
                if platform.label == "windows"
                else "COMPUTER_USE_PLATFORM_NOT_QUALIFIED"
            )
            checks.append(
                _check(
                    "platform",
                    False,
                    reason,
                    "Vision live execution is qualified only for supervised macOS pilots.",
                    "Run live vision computer-use on a qualified macOS pilot host.",
                )
            )
            return self._report(platform.label, checks)

        checks.append(
            _check(
                "vision_enabled",
                self.config.vision_enabled,
                None if self.config.vision_enabled else "VISION_RUNTIME_NOT_CONFIGURED",
                "Vision runtime feature flag is enabled."
                if self.config.vision_enabled
                else "Vision runtime feature flag is disabled.",
                "Set computer_use.vision_enabled=true only on a supervised pilot host.",
            )
        )
        checks.append(
            _check(
                "macos_live_enabled",
                self.config.macos_live_enabled,
                None if self.config.macos_live_enabled else "MACOS_COMPUTER_USE_NOT_ENABLED",
                "macOS live execution flag is enabled."
                if self.config.macos_live_enabled
                else "macOS live execution flag is disabled.",
                "Set computer_use.macos_live_enabled=true after local qualification.",
            )
        )
        provider_configured = self.config.vision_provider != "none" and bool(
            self.config.vision_model or self.config.vision_provider == "mock"
        )
        checks.append(
            _check(
                "vision_provider",
                provider_configured,
                None if provider_configured else "VISION_PROVIDER_UNAVAILABLE",
                "Vision provider is configured."
                if provider_configured
                else "Vision provider is not configured.",
                "Configure computer_use.vision_provider and computer_use.vision_model.",
            )
        )
        capture_available = self.config.macos_capture_backend == "screencapture" and bool(
            which("screencapture")
        )
        checks.append(
            _check(
                "screen_capture",
                capture_available,
                None if capture_available else "MACOS_CAPTURE_BACKEND_UNAVAILABLE",
                "screencapture backend is available."
                if capture_available
                else "screencapture backend is unavailable.",
                "Verify macOS Screen Recording permission and system capture tooling manually.",
            )
        )
        input_available = (
            input_backend_available
            if input_backend_available is not None
            else self.config.macos_input_backend == "quartz"
        )
        checks.append(
            _check(
                "accessibility_input",
                input_available,
                None if input_available else "MACOS_INPUT_BACKEND_UNAVAILABLE",
                "Quartz input backend is configured."
                if input_available
                else "Quartz input backend is unavailable or disabled.",
                (
                    "Install optional macOS computer-use dependencies and grant "
                    "Accessibility manually."
                ),
            )
        )
        checks.append(
            _check(
                "raw_screenshot_policy",
                self.config.raw_screenshot_retention == "disabled"
                and self.config.raw_screenshot_max_count == 0,
                None
                if self.config.raw_screenshot_retention == "disabled"
                and self.config.raw_screenshot_max_count == 0
                else "COMPUTER_USE_RAW_SCREENSHOT_DENIED",
                "Raw screenshot persistence is disabled by default.",
                (
                    "Keep raw_screenshot_retention=disabled unless using explicit "
                    "local debug evidence."
                ),
            )
        )
        if self.config.platform_qualification_required:
            checks.append(
                _check(
                    "qualification",
                    False,
                    "MACOS_COMPUTER_USE_QUALIFICATION_REQUIRED",
                    "Live execution requires signed local qualification evidence.",
                    "Run deterministic qualification, then opt-in live macOS qualification.",
                )
            )
        return self._report(platform.label, checks)

    @staticmethod
    def _report(platform: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "runtime": "computer_use_vision",
            "platform": platform,
            "stage": "configured" if all(item["ok"] for item in checks) else "blocked",
            "live_execution_allowed": all(item["ok"] for item in checks),
            "checks": checks,
        }


class MacOSScreenCaptureProvider:
    def __init__(
        self,
        *,
        config: ComputerUseRuntimeConfig,
        job_dir: Path,
        raw_screenshot_opt_in: bool = False,
        runner: Callable[..., Any] = subprocess.run,
        now: Callable[[], str] | None = None,
    ) -> None:
        self.config = config
        self.job_dir = Path(job_dir)
        self.raw_screenshot_opt_in = raw_screenshot_opt_in
        self.runner = runner
        self.now = now or (lambda: datetime.now(UTC).isoformat())
        self._persisted_count = 0

    def capture(self) -> VisionObservation:
        if self.config.macos_capture_backend != "screencapture":
            raise VisionRuntimeError(
                "MACOS_CAPTURE_BACKEND_UNAVAILABLE",
                "Only the screencapture backend is currently implemented.",
            )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            capture_path = Path(tmp.name)
        try:
            try:
                proc = self.runner(
                    ["screencapture", "-x", "-t", "png", str(capture_path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise VisionRuntimeError(
                    "MACOS_CAPTURE_BACKEND_UNAVAILABLE",
                    "macOS screencapture command is unavailable.",
                ) from exc
            if proc.returncode != 0:
                stderr = str(getattr(proc, "stderr", ""))
                reason = (
                    "MACOS_SCREEN_RECORDING_PERMISSION_MISSING"
                    if "permission" in stderr.lower() or "not authorized" in stderr.lower()
                    else "MACOS_CAPTURE_BACKEND_UNAVAILABLE"
                )
                raise VisionRuntimeError(reason, stderr or "screencapture failed")
            data = capture_path.read_bytes()
            screenshot_hash = hashlib.sha256(data).hexdigest()
            persisted_path = self._maybe_persist(data)
            return VisionObservation(
                screenshot_hash=screenshot_hash,
                raw_screenshot_path=str(persisted_path) if persisted_path else None,
                captured_at=self.now(),
                platform="macos",
                confidence=1.0,
            )
        finally:
            capture_path.unlink(missing_ok=True)

    def _maybe_persist(self, data: bytes) -> Path | None:
        allowed = (
            self.raw_screenshot_opt_in
            and self.config.raw_screenshot_retention == "explicit_opt_in"
            and self.config.raw_screenshot_max_count > self._persisted_count
        )
        if not allowed:
            return None
        screenshots_dir = self.job_dir / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        path = screenshots_dir / f"screen-{self._persisted_count + 1:04d}.png"
        path.write_bytes(data)
        self._persisted_count += 1
        return path


class MacOSInputExecutor:
    def __init__(
        self,
        *,
        config: ComputerUseRuntimeConfig,
        display_bounds: DisplayBounds | None = None,
        quartz_backend: Any | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config
        self.display_bounds = display_bounds or DisplayBounds(width=1440, height=900)
        self.quartz_backend = quartz_backend
        self.sleeper = sleeper

    def execute(self, action: VisionAction) -> ExecutionResult:
        started = time.perf_counter()
        if action.action_type.value not in self.config.action_set:
            return self._blocked(action, "COMPUTER_USE_APPROVAL_REQUIRED", started)
        if action.action_type in {InputActionType.TYPE_TEXT, InputActionType.HOTKEY}:
            return self._blocked(action, "COMPUTER_USE_APPROVAL_REQUIRED", started)
        if action.action_type == InputActionType.WAIT:
            wait_ms = min(action.wait_ms or 250, self.config.max_action_duration_ms)
            self.sleeper(wait_ms / 1000)
            return self._executed(action, started, {"wait_ms": wait_ms})
        if self.config.macos_input_backend != "quartz" or self.quartz_backend is None:
            return self._failed(action, "MACOS_INPUT_BACKEND_UNAVAILABLE", started)
        if action.target_bbox is None and action.action_type in {
            InputActionType.MOVE_MOUSE,
            InputActionType.CLICK,
            InputActionType.DOUBLE_CLICK,
        }:
            return self._blocked(action, "VISION_CONFIDENCE_BELOW_THRESHOLD", started)
        if action.action_type == InputActionType.HOTKEY and _hotkey_denied(action.hotkey):
            return self._blocked(action, "COMPUTER_USE_APPROVAL_REQUIRED", started)

        point = (
            normalized_bbox_center_to_pixel(action.target_bbox, self.display_bounds)
            if action.target_bbox is not None
            else (self.display_bounds.origin_x, self.display_bounds.origin_y)
        )
        if action.action_type == InputActionType.MOVE_MOUSE:
            self.quartz_backend.move_mouse(*point)
        elif action.action_type == InputActionType.CLICK:
            self.quartz_backend.click(*point, clicks=1)
        elif action.action_type == InputActionType.DOUBLE_CLICK:
            self.quartz_backend.click(*point, clicks=2)
        elif action.action_type == InputActionType.SCROLL:
            delta = max(min(action.scroll_delta or 0, 1200), -1200)
            if hasattr(self.quartz_backend, "scroll"):
                self.quartz_backend.scroll(delta)
        return self._executed(action, started, {"point": point})

    def _executed(
        self,
        action: VisionAction,
        started: float,
        details: dict[str, Any],
    ) -> ExecutionResult:
        return ExecutionResult(
            status="executed",
            message="macOS input action executed.",
            details={
                "action_id": action.action_id,
                "duration_ms": _duration_ms(started),
                "redacted": True,
                **details,
            },
        )

    def _failed(self, action: VisionAction, reason_code: str, started: float) -> ExecutionResult:
        return ExecutionResult(
            status="failed",
            message=reason_code,
            details={
                "action_id": action.action_id,
                "reason_code": reason_code,
                "duration_ms": _duration_ms(started),
                "redacted": True,
            },
        )

    def _blocked(self, action: VisionAction, reason_code: str, started: float) -> ExecutionResult:
        return ExecutionResult(
            status="blocked",
            message=reason_code,
            details={
                "action_id": action.action_id,
                "reason_code": reason_code,
                "duration_ms": _duration_ms(started),
                "redacted": True,
            },
        )


def normalized_bbox_center_to_pixel(
    bbox: NormalizedBBox,
    bounds: DisplayBounds,
) -> tuple[int, int]:
    raw_x = bounds.origin_x + round((bbox.x + bbox.w / 2) * bounds.width)
    raw_y = bounds.origin_y + round((bbox.y + bbox.h / 2) * bounds.height)
    return (
        max(bounds.origin_x, min(bounds.origin_x + bounds.width - 1, raw_x)),
        max(bounds.origin_y, min(bounds.origin_y + bounds.height - 1, raw_y)),
    )


def _check(
    key: str,
    ok: bool,
    reason_code: str | None,
    summary: str,
    remediation: str,
) -> dict[str, Any]:
    return {
        "key": key,
        "ok": ok,
        "reason_code": None if ok else reason_code,
        "summary": summary,
        "remediation": remediation,
    }


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _hotkey_denied(keys: list[str]) -> bool:
    normalized = {key.strip().lower() for key in keys}
    denied = [
        {"cmd", "q"},
        {"cmd", "delete"},
        {"cmd", "shift", "delete"},
    ]
    return any(combo.issubset(normalized) for combo in denied)
