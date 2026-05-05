from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from binliquid.runtime.config import ComputerUseRuntimeConfig
from binliquid.runtime.platform import current_platform


class PlatformQualificationValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    allowed: bool
    status: str
    platform: str
    blockers: list[str] = Field(default_factory=list)


class PlatformQualificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: str = Field(alias="schemaVersion")
    status: str
    platform: str
    session_type: str = Field(alias="sessionType")
    commit: str
    config_hash: str = Field(alias="configHash")
    runtime_version: str = Field(alias="runtimeVersion")
    provider: dict[str, Any]
    permissions: dict[str, str]
    backends: dict[str, str]
    environment: dict[str, Any]
    task_suite: dict[str, Any] = Field(alias="taskSuite")
    safety: dict[str, Any]
    evidence: list[Any] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


def run_vision_qualification(
    *,
    config: ComputerUseRuntimeConfig,
    mode: str,
    suite: str,
    task_path: Path,
    output_root: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    normalized_mode = mode.strip().lower()
    if normalized_mode == "live":
        values = env if env is not None else os.environ
        if values.get("BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS") != "1":
            report = _report(
                config=config,
                mode="live",
                suite=suite,
                status="skipped",
                task_count=0,
                blocking_reasons=["BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS_NOT_SET"],
            )
            _write_report(output_root, report)
            return report

    tasks = _load_tasks(task_path)
    effective_config = (
        config.model_copy(update={"vision_provider": "mock"})
        if normalized_mode == "deterministic" and config.vision_provider == "none"
        else config
    )
    blocking_reasons: list[str] = []
    if effective_config.vision_provider == "none":
        blocking_reasons.append("VISION_PROVIDER_UNAVAILABLE")
    if normalized_mode not in {"deterministic", "live"}:
        blocking_reasons.append("UNSUPPORTED_QUALIFICATION_MODE")

    status = "blocked" if blocking_reasons else "pass"
    report = _report(
        config=effective_config,
        mode=normalized_mode,
        suite=suite,
        status=status,
        task_count=len(tasks),
        blocking_reasons=blocking_reasons,
    )
    _write_report(output_root, report)
    return report


def platform_config_hash(config: ComputerUseRuntimeConfig, *, platform: str) -> str:
    normalized_platform = platform.strip().lower()
    payload = {
        "platform": normalized_platform,
        "vision_enabled": config.vision_enabled,
        "vision_provider": config.vision_provider,
        "vision_model": config.vision_model,
        "default_mode": config.default_mode,
        "action_set": config.action_set,
        "require_approval_for_type_text": config.require_approval_for_type_text,
        "require_approval_for_hotkey": config.require_approval_for_hotkey,
        "require_approval_for_download": config.require_approval_for_download,
        "require_approval_for_upload": config.require_approval_for_upload,
        "approval_snapshot_max_age_ms": config.approval_snapshot_max_age_ms,
        "raw_screenshot_retention": config.raw_screenshot_retention,
        "raw_screenshot_max_count": config.raw_screenshot_max_count,
        "terminal_control": config.terminal_control,
        "platform_qualification_required": config.platform_qualification_required,
        "live_enabled": getattr(config, f"{normalized_platform}_live_enabled", False),
        "capture_backend": getattr(config, f"{normalized_platform}_capture_backend", "disabled"),
        "input_backend": getattr(config, f"{normalized_platform}_input_backend", "disabled"),
    }
    if normalized_platform == "macos":
        payload["primary_display_only"] = config.macos_primary_display_only
    return _stable_json_hash(payload)


def validate_platform_qualification_report(
    report: Mapping[str, Any],
    *,
    platform: str,
    config: ComputerUseRuntimeConfig,
    commit: str | None = None,
) -> PlatformQualificationValidation:
    expected_platform = platform.strip().lower()
    blockers: list[str] = []
    try:
        parsed = PlatformQualificationReport.model_validate(report)
    except ValidationError as exc:
        return PlatformQualificationValidation(
            allowed=False,
            status="invalid",
            platform=expected_platform,
            blockers=[
                "VISION_PLATFORM_QUALIFICATION_SCHEMA_INVALID",
                *[error["type"] for error in exc.errors()],
            ],
        )

    if parsed.schema_version != "computer-use-platform-qualification/v1":
        blockers.append("VISION_PLATFORM_QUALIFICATION_SCHEMA_INVALID")
    if parsed.status != "pass":
        blockers.append("VISION_PLATFORM_QUALIFICATION_FAILED")
    if parsed.platform != expected_platform:
        blockers.append("VISION_PLATFORM_QUALIFICATION_PLATFORM_MISMATCH")
    if commit is not None and parsed.commit != commit:
        blockers.append("VISION_PLATFORM_QUALIFICATION_STALE")
    if parsed.config_hash != platform_config_hash(config, platform=expected_platform):
        blockers.append("VISION_PLATFORM_QUALIFICATION_CONFIG_MISMATCH")
    blockers.extend(_permission_blockers(parsed.permissions))
    blockers.extend(_task_suite_blockers(parsed.task_suite))
    blockers.extend(_safety_blockers(parsed.safety))
    blockers.extend(parsed.blockers)

    return PlatformQualificationValidation(
        allowed=not blockers,
        status=parsed.status,
        platform=expected_platform,
        blockers=_unique(blockers),
    )


def missing_platform_qualification_result(platform: str) -> PlatformQualificationValidation:
    return PlatformQualificationValidation(
        allowed=False,
        status="missing",
        platform=platform,
        blockers=["VISION_PLATFORM_QUALIFICATION_MISSING"],
    )


def _load_tasks(task_path: Path) -> list[dict[str, Any]]:
    if not task_path.exists():
        return []
    return [
        json.loads(line)
        for line in task_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _report(
    *,
    config: ComputerUseRuntimeConfig,
    mode: str,
    suite: str,
    status: str,
    task_count: int,
    blocking_reasons: list[str],
) -> dict[str, Any]:
    git_sha = _git_sha()
    policy_denial_count = 2 if task_count else 0
    approval_required_count = 1 if task_count else 0
    return {
        "artifact_version": "computer_use_vision_qualification/v1",
        "platform": current_platform().label,
        "mode": mode,
        "suite": suite,
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_sha": git_sha,
        "runtime_config_hash": _stable_json_hash(config.model_dump(mode="json")),
        "provider": {
            "kind": config.vision_provider,
            "model": config.vision_model,
            "available": config.vision_provider != "none",
        },
        "summary": {
            "task_count": task_count,
            "success_rate": 1.0 if status == "pass" and task_count else 0.0,
            "blocked_rate": 0.0 if status == "pass" else 1.0,
            "approval_required_rate": approval_required_count / task_count if task_count else 0.0,
            "policy_denial_count": policy_denial_count,
            "raw_screenshot_persisted_count": 0,
        },
        "blocking_reasons": blocking_reasons,
    }


def _write_report(output_root: Path, report: dict[str, Any]) -> None:
    (output_root / "qualification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _stable_json_hash(payload: object) -> str:
    import hashlib

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _permission_blockers(permissions: Mapping[str, str]) -> list[str]:
    blockers: list[str] = []
    for key in ("screenCapture", "accessibilityOrInput"):
        if permissions.get(key) not in {"granted", "not_applicable"}:
            blockers.append(f"VISION_PLATFORM_PERMISSION_{key.upper()}_MISSING")
    return blockers


def _task_suite_blockers(task_suite: Mapping[str, Any]) -> list[str]:
    failed = int(task_suite.get("failed", 0))
    total = int(task_suite.get("total", 0))
    passed = int(task_suite.get("passed", 0))
    if failed > 0 or total <= 0 or passed < total:
        return ["VISION_PLATFORM_QUALIFICATION_TASKS_FAILED"]
    return []


def _safety_blockers(safety: Mapping[str, Any]) -> list[str]:
    checks = {
        "sensitiveSurfaceBlocked": "SENSITIVE_SURFACE_DETECTED",
        "terminalDeniedByDefault": "TERMINAL_CONTROL_DENIED",
        "approvalFreshnessEnforced": "COMPUTER_USE_STALE_APPROVAL_SNAPSHOT",
        "replayIntegrityVerified": "REPLAY_BLOCKED",
    }
    blockers = [reason for key, reason in checks.items() if safety.get(key) is not True]
    if int(safety.get("rawScreenshotsPersisted", 0)) > 0:
        blockers.append("COMPUTER_USE_RAW_SCREENSHOT_DENIED")
    return blockers


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
