from __future__ import annotations

import os
from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from binliquid.computer_use.vision_runtime.qualification import (
    validate_platform_qualification_report,
)
from binliquid.runtime.config import ComputerUseRuntimeConfig
from binliquid.runtime.platform import current_platform as runtime_current_platform


class ComputerUsePlatform(StrEnum):
    MACOS = "macos"
    WINDOWS = "windows"
    LINUX = "linux"


PlatformStage = Literal[
    "unavailable",
    "disabled",
    "not_configured",
    "missing_permission",
    "provider_unavailable",
    "not_qualified",
    "qualified_available",
    "permission_ready",
    "provider_ready",
    "fixture_qualified",
    "qualified_limited",
    "enabled",
    "blocked",
    "ready_for_dry_run",
    "ready_for_step_approval",
    "qualified_supervised_pilot",
]


class PlatformCapability(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)

    platform: Literal["macos", "windows", "linux"]
    stage: PlatformStage
    live_enabled: bool = Field(alias="liveEnabled")
    capture_backend: str = Field(alias="captureBackend")
    input_backend: str = Field(alias="inputBackend")
    provider: str
    permissions: list[str] = Field(default_factory=list)
    execution_modes: list[str] = Field(
        default_factory=lambda: ["dry_run", "step_approval"],
        alias="executionModes",
    )
    replayable: bool = True
    fail_closed: bool = Field(default=True, alias="failClosed")
    reason_code: str | None = Field(default=None, alias="reasonCode")
    summary: str | None = None
    blockers: list[str] = Field(default_factory=list)
    qualification_status: str = Field(default="missing", alias="qualificationStatus")
    environment: dict[str, str] = Field(default_factory=dict)


PLATFORM_REASON_CODES: dict[ComputerUsePlatform, str] = {
    ComputerUsePlatform.MACOS: "MACOS_COMPUTER_USE_NOT_QUALIFIED",
    ComputerUsePlatform.WINDOWS: "WINDOWS_COMPUTER_USE_NOT_QUALIFIED",
    ComputerUsePlatform.LINUX: "LINUX_COMPUTER_USE_NOT_QUALIFIED",
}

CAPTURE_DISABLED_CODES: dict[ComputerUsePlatform, str] = {
    ComputerUsePlatform.MACOS: "MACOS_CAPTURE_BACKEND_DISABLED",
    ComputerUsePlatform.WINDOWS: "WINDOWS_CAPTURE_BACKEND_DISABLED",
    ComputerUsePlatform.LINUX: "LINUX_CAPTURE_BACKEND_DISABLED",
}

INPUT_DISABLED_CODES: dict[ComputerUsePlatform, str] = {
    ComputerUsePlatform.MACOS: "MACOS_INPUT_BACKEND_DISABLED",
    ComputerUsePlatform.WINDOWS: "WINDOWS_INPUT_BACKEND_DISABLED",
    ComputerUsePlatform.LINUX: "LINUX_INPUT_BACKEND_DISABLED",
}


def build_platform_capabilities(
    config: ComputerUseRuntimeConfig,
    *,
    environment: Mapping[str, str] | None = None,
    qualification_reports: Mapping[str, Mapping[str, Any]] | None = None,
    commit: str | None = None,
) -> dict[str, PlatformCapability]:
    return {
        platform.value: build_platform_capability(
            config,
            platform=platform,
            environment=environment,
            qualification_report=(qualification_reports or {}).get(platform.value),
            commit=commit,
        )
        for platform in ComputerUsePlatform
    }


def build_platform_capability(
    config: ComputerUseRuntimeConfig,
    *,
    platform: ComputerUsePlatform | str,
    environment: Mapping[str, str] | None = None,
    qualification_report: Mapping[str, Any] | None = None,
    commit: str | None = None,
) -> PlatformCapability:
    normalized_platform = _normalize_platform(platform)
    env = dict(environment or os.environ)
    capture_backend = _capture_backend(config, normalized_platform)
    input_backend = _input_backend(config, normalized_platform)
    provider_configured = _provider_configured(config)
    live_requested = _live_requested(config, normalized_platform)
    blockers = _base_blockers(config, normalized_platform, env)

    qualification_status = "missing"
    qualification_allowed = False
    if qualification_report is not None:
        validation = validate_platform_qualification_report(
            qualification_report,
            platform=normalized_platform.value,
            config=config,
            commit=commit,
        )
        qualification_status = validation.status
        qualification_allowed = validation.allowed
        blockers.extend(validation.blockers)
    elif live_requested and config.platform_qualification_required:
        blockers.append("VISION_PLATFORM_QUALIFICATION_MISSING")

    safety_defaults_ok = (
        config.raw_screenshot_persistence is False
        and config.raw_screenshot_retention == "disabled"
        and config.raw_screenshot_max_count == 0
        and config.terminal_control == "deny"
        and config.sensitive_surface_policy == "stop"
    )
    live_enabled = (
        live_requested
        and (qualification_allowed or not config.platform_qualification_required)
        and safety_defaults_ok
    )
    if live_enabled:
        stage: PlatformStage = "qualified_limited"
        reason_code = None
    elif (
        normalized_platform == ComputerUsePlatform.MACOS
        and qualification_allowed
        and not _platform_live_flag(config, normalized_platform)
    ):
        stage = "fixture_qualified"
        reason_code = "MACOS_LIVE_FLAG_DISABLED"
    else:
        stage = "not_qualified"
        reason_code = PLATFORM_REASON_CODES[normalized_platform]
    execution_modes = ["dry_run", "step_approval"]
    if live_enabled:
        execution_modes.append("execute")

    return PlatformCapability(
        platform=normalized_platform.value,
        stage=stage,
        liveEnabled=live_enabled,
        captureBackend=capture_backend,
        inputBackend=input_backend,
        provider=config.vision_provider,
        permissions=_required_permissions(normalized_platform),
        executionModes=execution_modes,
        replayable=True,
        failClosed=True,
        reasonCode=reason_code,
        summary=_summary(normalized_platform, live_enabled, provider_configured),
        blockers=_unique(blockers),
        qualificationStatus=qualification_status,
        environment=_environment_snapshot(normalized_platform, env),
    )


def evaluate_platform_matrix(
    config: ComputerUseRuntimeConfig,
    *,
    current_platform: str | None = None,
    environment: Mapping[str, str] | None = None,
    qualification_reports: Mapping[str, Mapping[str, Any]] | None = None,
    commit: str | None = None,
) -> dict[str, Any]:
    capabilities = build_platform_capabilities(
        config,
        environment=environment,
        qualification_reports=qualification_reports,
        commit=commit,
    )
    blockers = [
        f"{platform.value}_live_ready_without_valid_qualification"
        for platform in ComputerUsePlatform
        if _live_requested(config, platform) and not capabilities[platform.value].live_enabled
    ]
    raw_screenshot_default = (
        config.raw_screenshot_retention != "disabled" or config.raw_screenshot_max_count > 0
    )
    if raw_screenshot_default:
        blockers.append("raw_screenshot_persistence_enabled_by_default")
    if config.terminal_control != "deny":
        blockers.append("terminal_control_not_denied_by_default")

    return {
        "schemaVersion": "computer-use-platform-matrix/v1",
        "runtime": "computer_use_vision",
        "profile": "unknown",
        "currentPlatform": current_platform or runtime_current_platform().label,
        "status": "fail" if blockers else "pass",
        "liveAutomationDefault": False,
        "rawScreenshotPersistenceDefault": raw_screenshot_default,
        "terminalControlDefault": config.terminal_control,
        "securityInvariants": {
            "screenTextTreatedAsUntrusted": True,
            "sensitiveSurfaceBlocked": True,
            "terminalDeniedByDefault": config.terminal_control == "deny",
            "approvalFreshnessEnforced": True,
            "replayIntegrityVerified": True,
            "rawScreenshotsPersistedByDefault": raw_screenshot_default,
        },
        "platforms": {
            key: capability.model_dump(mode="json", by_alias=True)
            for key, capability in capabilities.items()
        },
        "blockers": blockers,
    }


def _normalize_platform(platform: ComputerUsePlatform | str) -> ComputerUsePlatform:
    if isinstance(platform, ComputerUsePlatform):
        return platform
    return ComputerUsePlatform(str(platform).strip().lower())


def _provider_configured(config: ComputerUseRuntimeConfig) -> bool:
    if config.vision_provider == "none":
        return False
    if config.vision_provider == "mock":
        return True
    return bool(config.vision_model)


def _live_requested(config: ComputerUseRuntimeConfig, platform: ComputerUsePlatform) -> bool:
    return (
        config.enabled
        and config.vision_enabled
        and _provider_configured(config)
        and _platform_live_flag(config, platform)
        and _capture_backend(config, platform) != "disabled"
        and _input_backend(config, platform) != "disabled"
    )


def _base_blockers(
    config: ComputerUseRuntimeConfig,
    platform: ComputerUsePlatform,
    environment: Mapping[str, str],
) -> list[str]:
    blockers: list[str] = []
    if not config.enabled or not config.vision_enabled:
        blockers.append("VISION_RUNTIME_DISABLED")
    if not _provider_configured(config):
        blockers.append("VISION_PROVIDER_UNAVAILABLE")
    if _capture_backend(config, platform) == "disabled":
        blockers.append(CAPTURE_DISABLED_CODES[platform])
    if _input_backend(config, platform) == "disabled":
        blockers.append(INPUT_DISABLED_CODES[platform])
    if (
        config.raw_screenshot_persistence
        or config.raw_screenshot_retention != "disabled"
        or config.raw_screenshot_max_count > 0
    ):
        blockers.append("COMPUTER_USE_RAW_SCREENSHOT_DENIED")
    if config.terminal_control != "deny":
        blockers.append("COMPUTER_USE_TERMINAL_CONTROL_DENIED")
    if config.sensitive_surface_policy != "stop":
        blockers.append("COMPUTER_USE_SENSITIVE_SURFACE_DETECTED")
    if platform == ComputerUsePlatform.WINDOWS:
        blockers.append("WINDOWS_UAC_SECURE_DESKTOP_BLOCKED")
    if platform == ComputerUsePlatform.LINUX:
        blockers.extend(_linux_session_blockers(environment))
    return blockers


def _linux_session_blockers(environment: Mapping[str, str]) -> list[str]:
    session_type = environment.get("XDG_SESSION_TYPE", "").strip().lower()
    wayland_display = environment.get("WAYLAND_DISPLAY", "").strip()
    x11_display = environment.get("DISPLAY", "").strip()
    if session_type == "wayland" or wayland_display:
        return ["LINUX_WAYLAND_NOT_QUALIFIED"]
    if session_type == "x11" or x11_display:
        return ["LINUX_X11_NOT_QUALIFIED"]
    return ["LINUX_SESSION_NOT_DETECTED"]


def _platform_live_flag(config: ComputerUseRuntimeConfig, platform: ComputerUsePlatform) -> bool:
    return bool(getattr(config, f"{platform.value}_live_enabled"))


def _capture_backend(config: ComputerUseRuntimeConfig, platform: ComputerUsePlatform) -> str:
    return str(getattr(config, f"{platform.value}_capture_backend"))


def _input_backend(config: ComputerUseRuntimeConfig, platform: ComputerUsePlatform) -> str:
    return str(getattr(config, f"{platform.value}_input_backend"))


def _required_permissions(platform: ComputerUsePlatform) -> list[str]:
    if platform == ComputerUsePlatform.MACOS:
        return ["screen_recording", "accessibility"]
    if platform == ComputerUsePlatform.WINDOWS:
        return ["screen_capture", "input_injection", "secure_desktop_guard"]
    return ["screen_capture", "input_injection", "session_guard"]


def _environment_snapshot(
    platform: ComputerUsePlatform,
    environment: Mapping[str, str],
) -> dict[str, str]:
    if platform != ComputerUsePlatform.LINUX:
        return {}
    return {
        key: environment.get(key, "")
        for key in ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY")
    }


def _summary(
    platform: ComputerUsePlatform,
    live_enabled: bool,
    provider_configured: bool,
) -> str:
    if live_enabled:
        return f"{platform.value} supervised computer-use is qualification-gated and enabled."
    if not provider_configured:
        return (
            f"{platform.value} vision runtime is fail-closed until a provider "
            "and qualification pass."
        )
    return f"{platform.value} vision runtime is configured but not qualified for live execution."


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
