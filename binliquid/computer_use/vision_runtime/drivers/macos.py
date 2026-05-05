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
from binliquid.computer_use.vision_runtime.qualification import (
    validate_platform_qualification_report,
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
        environment: Mapping[str, str] | None = None,
        qualification_report: Mapping[str, Any] | None = None,
        commit: str | None = None,
        which: Callable[[str], str | None] = shutil.which,
        input_backend_available: bool | None = None,
    ) -> dict[str, Any]:
        platform = platform_info or current_platform()
        env = dict(environment or {})
        checks: list[dict[str, Any]] = []
        if platform.label != "macos":
            reason = (
                "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
                if platform.label == "windows"
                else "LINUX_COMPUTER_USE_NOT_QUALIFIED"
            )
            checks.append(
                _check(
                    "platform",
                    False,
                    reason,
                    "Vision live execution remains gated to supervised macOS qualification.",
                    "Use live vision computer-use only with valid macOS qualification evidence.",
                )
            )
            return self._report(
                platform.label,
                checks,
                stage="not_qualified",
                live_enabled=False,
                reason_code=reason,
                permissions=_permissions_payload(
                    screen_recording="unknown",
                    accessibility="unknown",
                    input_monitoring="not_required",
                ),
                provider=_provider_payload(
                    configured=False,
                    name=self.config.vision_provider,
                    model=self.config.vision_model or "",
                    strict_json=False,
                    ready=False,
                    reason_code="VISION_PROVIDER_UNAVAILABLE",
                ),
                capture={"backend": "disabled", "ready": False},
                input_state={"backend": "disabled", "ready": False},
                qualification=_qualification_payload(
                    required=True,
                    present=False,
                    valid=False,
                    fresh=False,
                    report_path=self.config.macos_qualification_report,
                    reason_code="MACOS_QUALIFICATION_REPORT_MISSING",
                ),
            )

        screen_recording = _env_permission_status(
            env,
            "BINLIQUID_COMPUTER_USE_MACOS_SCREEN_RECORDING",
            "BINLIQUID_TEST_MACOS_SCREEN_RECORDING",
        )
        accessibility = _env_permission_status(
            env,
            "BINLIQUID_COMPUTER_USE_MACOS_ACCESSIBILITY",
            "BINLIQUID_TEST_MACOS_ACCESSIBILITY",
        )
        provider = _evaluate_provider(self.config, which=which)
        capture = _evaluate_capture(
            self.config,
            which=which,
            screen_recording=screen_recording,
        )
        input_state = _evaluate_input(
            self.config,
            accessibility=accessibility,
            input_backend_available=input_backend_available,
        )
        qualification = _evaluate_qualification(
            self.config,
            qualification_report=qualification_report,
            commit=commit,
        )

        checks.append(
            _check(
                "vision_enabled",
                self.config.vision_enabled,
                None if self.config.vision_enabled else "VISION_RUNTIME_DISABLED",
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
                None if self.config.macos_live_enabled else "MACOS_LIVE_FLAG_DISABLED",
                "macOS live execution flag is enabled."
                if self.config.macos_live_enabled
                else "macOS live execution flag is disabled.",
                "Set computer_use.macos_live_enabled=true after local qualification.",
            )
        )
        checks.append(
            _check(
                "vision_provider",
                bool(provider["ready"]),
                None if provider["ready"] else str(provider["reasonCode"]),
                "Vision provider is configured and ready."
                if provider["ready"]
                else "Vision provider is not ready.",
                "Configure computer_use.vision_provider and computer_use.vision_model.",
            )
        )
        checks.append(
            _check(
                "screen_capture",
                bool(capture["ready"]),
                None if capture["ready"] else str(capture["reasonCode"]),
                "macOS capture backend is ready."
                if capture["ready"]
                else "macOS capture backend is unavailable or disabled.",
                "Verify macOS Screen Recording permission and system capture tooling manually.",
            )
        )
        checks.append(
            _check(
                "accessibility_input",
                bool(input_state["ready"]),
                None if input_state["ready"] else str(input_state["reasonCode"]),
                "Quartz input backend is configured."
                if input_state["ready"]
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
                self.config.raw_screenshot_persistence is False
                and self.config.raw_screenshot_retention == "disabled"
                and self.config.raw_screenshot_max_count == 0,
                None
                if self.config.raw_screenshot_persistence is False
                and self.config.raw_screenshot_retention == "disabled"
                and self.config.raw_screenshot_max_count == 0
                else "RAW_SCREENSHOT_PERSISTENCE_DENIED",
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
                    bool(qualification["fresh"]),
                    None if qualification["fresh"] else str(qualification["reasonCode"]),
                    "Fresh macOS qualification evidence is present."
                    if qualification["fresh"]
                    else "Live execution requires fresh local qualification evidence.",
                    "Run deterministic qualification, then opt-in live macOS qualification.",
                )
            )
        stage, live_enabled, reason_code = _derive_stage(
            config=self.config,
            provider=provider,
            capture=capture,
            input_state=input_state,
            qualification=qualification,
            screen_recording=screen_recording,
            accessibility=accessibility,
        )
        return self._report(
            platform.label,
            checks,
            stage=stage,
            live_enabled=live_enabled,
            reason_code=reason_code,
            permissions=_permissions_payload(
                screen_recording=screen_recording,
                accessibility=accessibility,
                input_monitoring="not_required",
            ),
            provider=provider,
            capture=capture,
            input_state=input_state,
            qualification=qualification,
        )

    @staticmethod
    def _report(
        platform: str,
        checks: list[dict[str, Any]],
        *,
        stage: str,
        live_enabled: bool,
        reason_code: str | None,
        permissions: dict[str, str],
        provider: dict[str, Any],
        capture: dict[str, Any],
        input_state: dict[str, Any],
        qualification: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "runtime": "computer_use_vision",
            "platform": platform,
            "stage": stage,
            "liveEnabled": live_enabled,
            "reasonCode": reason_code,
            "permissions": permissions,
            "provider": provider,
            "capture": capture,
            "input": input_state,
            "qualification": qualification,
            "safety": {
                "privacyMode": True,
                "rawScreenshotPersistence": False,
                "rawScreenshotMaxCount": 0,
                "terminalPolicy": "deny",
                "sensitiveSurfacePolicy": "stop",
                "approvalFreshnessEnforced": True,
                "replayIntegrityEnforced": True,
            },
            "live_execution_allowed": live_enabled,
            "checks": checks,
        }


def _env_permission_status(
    environment: Mapping[str, str],
    *keys: str,
) -> str:
    for key in keys:
        value = environment.get(key)
        if value is None:
            continue
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "granted"}:
            return "granted"
        if normalized in {"0", "false", "no", "missing", "denied"}:
            return "missing"
        if normalized == "unknown":
            return "unknown"
    return "unknown"


def _provider_payload(
    *,
    configured: bool,
    name: str,
    model: str,
    strict_json: bool,
    ready: bool,
    reason_code: str | None,
) -> dict[str, Any]:
    return {
        "configured": configured,
        "name": name,
        "model": model,
        "strictJson": strict_json,
        "ready": ready,
        "reasonCode": reason_code,
    }


def _evaluate_provider(
    config: ComputerUseRuntimeConfig,
    *,
    which: Callable[[str], str | None],
) -> dict[str, Any]:
    configured = config.vision_enabled and config.vision_provider != "none" and bool(
        config.vision_model
    )
    if not configured:
        return _provider_payload(
            configured=False,
            name=config.vision_provider,
            model=config.vision_model or "",
            strict_json=False,
            ready=False,
            reason_code="VISION_PROVIDER_UNAVAILABLE",
        )
    if config.vision_provider != "ollama":
        return _provider_payload(
            configured=True,
            name=config.vision_provider,
            model=config.vision_model or "",
            strict_json=True,
            ready=False,
            reason_code="MACOS_PROVIDER_NOT_READY",
        )
    ready = bool(which("ollama"))
    return _provider_payload(
        configured=True,
        name="ollama",
        model=config.vision_model or "",
        strict_json=True,
        ready=ready,
        reason_code=None if ready else "VISION_PROVIDER_UNAVAILABLE",
    )


def _evaluate_capture(
    config: ComputerUseRuntimeConfig,
    *,
    which: Callable[[str], str | None],
    screen_recording: str,
) -> dict[str, Any]:
    backend = config.macos_capture_backend
    if backend == "disabled":
        return {
            "backend": backend,
            "ready": False,
            "reasonCode": "MACOS_CAPTURE_BACKEND_DISABLED",
        }
    tooling_ready = backend != "screencapture" or bool(which("screencapture"))
    if not tooling_ready:
        return {
            "backend": backend,
            "ready": False,
            "reasonCode": "MACOS_CAPTURE_BACKEND_UNAVAILABLE",
        }
    if screen_recording != "granted":
        return {
            "backend": backend,
            "ready": False,
            "reasonCode": "MACOS_SCREEN_RECORDING_PERMISSION_MISSING",
        }
    return {"backend": backend, "ready": True, "reasonCode": None}


def _evaluate_input(
    config: ComputerUseRuntimeConfig,
    *,
    accessibility: str,
    input_backend_available: bool | None,
) -> dict[str, Any]:
    backend = config.macos_input_backend
    if backend == "disabled":
        return {
            "backend": backend,
            "ready": False,
            "reasonCode": "MACOS_INPUT_BACKEND_DISABLED",
        }
    if accessibility != "granted":
        return {
            "backend": backend,
            "ready": False,
            "reasonCode": "MACOS_ACCESSIBILITY_PERMISSION_MISSING",
        }
    ready = input_backend_available if input_backend_available is not None else backend == "quartz"
    return {
        "backend": backend,
        "ready": bool(ready),
        "reasonCode": None if ready else "MACOS_INPUT_BACKEND_UNAVAILABLE",
    }


def _evaluate_qualification(
    config: ComputerUseRuntimeConfig,
    *,
    qualification_report: Mapping[str, Any] | None,
    commit: str | None,
) -> dict[str, Any]:
    if not config.platform_qualification_required:
        return _qualification_payload(
            required=False,
            present=False,
            valid=True,
            fresh=True,
            report_path=config.macos_qualification_report,
            reason_code=None,
        )
    if qualification_report is None:
        return _qualification_payload(
            required=True,
            present=False,
            valid=False,
            fresh=False,
            report_path=config.macos_qualification_report,
            reason_code="MACOS_QUALIFICATION_REPORT_MISSING",
        )
    validation = validate_platform_qualification_report(
        qualification_report,
        platform="macos",
        config=config,
        commit=commit,
    )
    reason_code = validation.blockers[0] if validation.blockers else None
    return _qualification_payload(
        required=True,
        present=True,
        valid=validation.status != "invalid",
        fresh=validation.allowed,
        report_path=config.macos_qualification_report,
        reason_code=reason_code,
    )


def _qualification_payload(
    *,
    required: bool,
    present: bool,
    valid: bool,
    fresh: bool,
    report_path: str,
    reason_code: str | None = None,
) -> dict[str, Any]:
    return {
        "required": required,
        "present": present,
        "valid": valid,
        "fresh": fresh,
        "reportPath": report_path,
        "reasonCode": reason_code,
    }


def _permissions_payload(
    *,
    screen_recording: str,
    accessibility: str,
    input_monitoring: str,
) -> dict[str, str]:
    return {
        "screenRecording": screen_recording,
        "accessibility": accessibility,
        "inputMonitoring": input_monitoring,
    }


def _derive_stage(
    *,
    config: ComputerUseRuntimeConfig,
    provider: Mapping[str, Any],
    capture: Mapping[str, Any],
    input_state: Mapping[str, Any],
    qualification: Mapping[str, Any],
    screen_recording: str,
    accessibility: str,
) -> tuple[str, bool, str | None]:
    if config.raw_screenshot_persistence or config.raw_screenshot_max_count != 0:
        return "blocked", False, "RAW_SCREENSHOT_PERSISTENCE_DENIED"
    if config.terminal_control != "deny":
        return "blocked", False, "TERMINAL_CONTROL_DENIED"
    if config.sensitive_surface_policy != "stop":
        return "blocked", False, "SENSITIVE_SURFACE_BLOCKED"
    if not config.macos_live_enabled:
        stage = "qualified_available" if qualification.get("fresh") else "not_configured"
        return stage, False, "MACOS_LIVE_FLAG_DISABLED"
    if not config.vision_enabled:
        return "not_configured", False, "VISION_RUNTIME_DISABLED"
    if capture.get("reasonCode") == "MACOS_CAPTURE_BACKEND_DISABLED":
        return "not_configured", False, "MACOS_CAPTURE_BACKEND_DISABLED"
    if input_state.get("reasonCode") == "MACOS_INPUT_BACKEND_DISABLED":
        return "not_configured", False, "MACOS_INPUT_BACKEND_DISABLED"
    if screen_recording != "granted":
        return "missing_permission", False, "MACOS_SCREEN_RECORDING_PERMISSION_MISSING"
    if accessibility != "granted":
        return "missing_permission", False, "MACOS_ACCESSIBILITY_PERMISSION_MISSING"
    if not provider.get("ready"):
        return "provider_unavailable", False, str(provider.get("reasonCode"))
    if qualification.get("required") and not qualification.get("fresh"):
        return "not_qualified", False, str(qualification.get("reasonCode"))
    if not config.macos_live_enabled:
        return "qualified_available", False, "MACOS_LIVE_FLAG_DISABLED"
    return "enabled", True, None


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
            reason = (
                "MACOS_CAPTURE_BACKEND_DISABLED"
                if self.config.macos_capture_backend == "disabled"
                else "MACOS_CAPTURE_BACKEND_UNAVAILABLE"
            )
            raise VisionRuntimeError(
                reason,
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
            dimensions = _png_dimensions(data)
            persisted_path = self._maybe_persist(data)
            return VisionObservation(
                screenshot_hash=screenshot_hash,
                raw_screenshot_path=str(persisted_path) if persisted_path else None,
                captured_at=self.now(),
                platform="macos",
                image_width=dimensions[0] if dimensions else None,
                image_height=dimensions[1] if dimensions else None,
                confidence=1.0,
            )
        finally:
            capture_path.unlink(missing_ok=True)

    def _maybe_persist(self, data: bytes) -> Path | None:
        allowed = (
            self.raw_screenshot_opt_in
            and self.config.raw_screenshot_persistence
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
        if action.action_type in {
            InputActionType.TYPE_TEXT,
            InputActionType.PRESS_KEY,
            InputActionType.HOTKEY,
            InputActionType.FOCUS_WINDOW_OR_APP,
        }:
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
            InputActionType.RIGHT_CLICK,
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
        elif action.action_type == InputActionType.RIGHT_CLICK:
            self.quartz_backend.click(*point, clicks=1, button="right")
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


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


def _hotkey_denied(keys: list[str]) -> bool:
    normalized = {key.strip().lower() for key in keys}
    denied = [
        {"cmd", "q"},
        {"cmd", "delete"},
        {"cmd", "shift", "delete"},
    ]
    return any(combo.issubset(normalized) for combo in denied)
