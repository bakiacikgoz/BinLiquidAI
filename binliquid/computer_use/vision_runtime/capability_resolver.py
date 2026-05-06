from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from binliquid.computer_use.vision_runtime.drivers import PlatformDriverReadiness
from binliquid.computer_use.vision_runtime.evidence import (
    QualificationEvidence,
    QualificationEvidenceValidation,
    validate_qualification_evidence,
)
from binliquid.runtime.config import ComputerUseRuntimeConfig


class CapabilityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EvidenceLoadStatus(StrEnum):
    MISSING = "missing"
    INVALID = "invalid"
    VALID = "valid"


class CapabilityStatus(StrEnum):
    PASS = "pass"
    BLOCKED = "blocked"
    FAIL = "fail"


class PlatformLiveMode(StrEnum):
    DISABLED = "disabled"
    DRY_RUN = "dry_run"
    STEP_APPROVAL = "step_approval"
    SUPERVISED_QUALIFICATION = "supervised_qualification"


class EvidenceSource(CapabilityModel):
    path: str | None = None
    load_status: EvidenceLoadStatus
    validation_status: str | None = None
    reason_code: str | None = None
    checked_at: str


class PlatformCapabilityResolution(CapabilityModel):
    platform: Literal["macos", "windows", "linux"]
    status: CapabilityStatus
    live_enabled: bool
    public_live_claim_allowed: bool
    fail_closed: bool
    reason_code: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    execution_modes: list[PlatformLiveMode] = Field(default_factory=list)
    evidence: EvidenceSource
    config_hash_match: bool | None = None
    commit_match: bool | None = None
    provider_match: bool | None = None
    backend_match: bool | None = None
    driver_ready: bool | None = None
    driver_reason_code: str | None = None
    permission_checks_passed: bool | None = None
    raw_screenshot_persistence_allowed: bool


class ComputerUseCapabilityResolution(CapabilityModel):
    artifact_version: Literal["computer-use-capability-resolution/v1"] = (
        "computer-use-capability-resolution/v1"
    )
    status: CapabilityStatus
    current_platform: Literal["macos", "windows", "linux", "unknown"]
    profile: str
    public_live_claim_allowed: bool
    platforms: dict[str, PlatformCapabilityResolution]


PLATFORM_REASON_CODES = {
    "macos": "MACOS_COMPUTER_USE_NOT_QUALIFIED",
    "windows": "WINDOWS_COMPUTER_USE_NOT_QUALIFIED",
    "linux": "LINUX_COMPUTER_USE_NOT_QUALIFIED",
}

EVIDENCE_REASON_MAP = {
    "QUALIFICATION_EVIDENCE_SCHEMA_INVALID": "COMPUTER_USE_EVIDENCE_INVALID_SCHEMA",
    "QUALIFICATION_EVIDENCE_STALE": "COMPUTER_USE_EVIDENCE_STALE",
    "QUALIFICATION_EVIDENCE_COMMIT_MISMATCH": "COMPUTER_USE_EVIDENCE_COMMIT_MISMATCH",
    "QUALIFICATION_EVIDENCE_PLATFORM_MISMATCH": "COMPUTER_USE_EVIDENCE_PLATFORM_MISMATCH",
    "QUALIFICATION_EVIDENCE_PROVIDER_MISMATCH": "COMPUTER_USE_EVIDENCE_PROVIDER_MISMATCH",
    "QUALIFICATION_EVIDENCE_BACKEND_MISMATCH": "COMPUTER_USE_EVIDENCE_BACKEND_MISMATCH",
    "RAW_SCREENSHOT_PERSISTENCE_DETECTED": "COMPUTER_USE_RAW_SCREENSHOT_INVARIANT_FAILED",
    "PUBLIC_LIVE_CLAIM_NOT_ALLOWED": "COMPUTER_USE_PUBLIC_LIVE_CLAIM_BLOCKED",
    "QUALIFICATION_EVIDENCE_PROVIDER_NOT_VERIFIED": "COMPUTER_USE_EVIDENCE_PROVIDER_MISMATCH",
    "QUALIFICATION_EVIDENCE_PERMISSION_MISSING": "COMPUTER_USE_PERMISSION_CHECK_FAILED",
    "SENSITIVE_SURFACE_STOP_NOT_VERIFIED": "COMPUTER_USE_EVIDENCE_FAILED",
    "APPROVAL_SNAPSHOT_BINDING_NOT_VERIFIED": "COMPUTER_USE_EVIDENCE_FAILED",
    "SEMANTIC_VERIFIER_NOT_VERIFIED": "COMPUTER_USE_EVIDENCE_FAILED",
    "REPLAY_INTEGRITY_NOT_VERIFIED": "COMPUTER_USE_EVIDENCE_FAILED",
}


def resolve_computer_use_capabilities(
    *,
    config: ComputerUseRuntimeConfig,
    profile: str,
    current_platform: str,
    current_commit: str | None = None,
    now: datetime | None = None,
    evidence_by_platform: Mapping[str, object] | None = None,
    evidence_paths: Mapping[str, str] | None = None,
    driver_readiness_by_platform: Mapping[str, object] | None = None,
) -> ComputerUseCapabilityResolution:
    checked_at = (now or datetime.now(UTC)).isoformat()
    normalized_current_platform = _normalize_current_platform(current_platform)
    platforms = {
        platform: _resolve_platform(
            platform=platform,
            current_platform=normalized_current_platform,
            config=config,
            profile=profile,
            current_commit=current_commit,
            now=now,
            evidence_payload=(evidence_by_platform or {}).get(platform),
            evidence_path=(evidence_paths or {}).get(platform),
            driver_readiness_payload=(driver_readiness_by_platform or {}).get(platform),
            checked_at=checked_at,
        )
        for platform in ("macos", "windows", "linux")
    }
    current_resolution = platforms.get(normalized_current_platform)
    status = (
        current_resolution.status
        if current_resolution is not None
        else _aggregate_status(platforms)
    )
    return ComputerUseCapabilityResolution(
        status=status,
        current_platform=normalized_current_platform,
        profile=profile,
        public_live_claim_allowed=False,
        platforms=platforms,
    )


def _resolve_platform(
    *,
    platform: str,
    current_platform: str,
    config: ComputerUseRuntimeConfig,
    profile: str,
    current_commit: str | None,
    now: datetime | None,
    evidence_payload: object | None,
    evidence_path: str | None,
    driver_readiness_payload: object | None,
    checked_at: str,
) -> PlatformCapabilityResolution:
    del profile
    blockers: list[str] = []
    warnings: list[str] = []
    evidence_source = EvidenceSource(
        path=evidence_path,
        load_status=EvidenceLoadStatus.MISSING,
        validation_status=None,
        reason_code="COMPUTER_USE_EVIDENCE_MISSING",
        checked_at=checked_at,
    )
    validation: QualificationEvidenceValidation | None = None
    evidence: QualificationEvidence | None = None
    if evidence_payload is None:
        blockers.append("COMPUTER_USE_EVIDENCE_MISSING")
    else:
        validation = validate_qualification_evidence(
            evidence_payload,
            current_platform=platform,
            current_commit=current_commit,
            now=now,
        )
        evidence = validation.evidence
        evidence_source = _evidence_source(
            validation=validation,
            path=evidence_path,
            checked_at=checked_at,
        )
        blockers.extend(_mapped_reasons(validation.reason_codes))
        if validation.status == "fail":
            blockers.append("COMPUTER_USE_EVIDENCE_FAILED")
        if evidence is not None and evidence.status == "blocked":
            blockers.extend(_mapped_reasons(evidence.reason_codes))

    if evidence is not None and evidence.platform.value != platform:
        blockers.append("COMPUTER_USE_EVIDENCE_PLATFORM_MISMATCH")
    if platform != current_platform and evidence is not None and evidence.status.value == "pass":
        blockers.append("COMPUTER_USE_EVIDENCE_PLATFORM_MISMATCH")

    provider_match = _provider_match(evidence, config)
    backend_match = _backend_match(evidence, config, platform)
    driver_ready, driver_reason_code, driver_blockers = _driver_readiness(
        driver_readiness_payload,
        platform=platform,
    )
    blockers.extend(driver_blockers)
    permission_checks_passed = _permission_checks_passed(evidence)
    commit_match = _commit_match(evidence, current_commit)
    raw_screenshot_ok = _raw_screenshot_ok(config, evidence)
    if not raw_screenshot_ok:
        blockers.append("COMPUTER_USE_RAW_SCREENSHOT_INVARIANT_FAILED")

    live_requested = _live_requested(config, platform)
    if evidence is not None and evidence.status.value == "pass" and not live_requested:
        blockers.append("COMPUTER_USE_CONFIG_LIVE_DISABLED")

    if provider_match is False:
        blockers.append("COMPUTER_USE_EVIDENCE_PROVIDER_MISMATCH")
    if backend_match is False:
        blockers.append("COMPUTER_USE_EVIDENCE_BACKEND_MISMATCH")
    if permission_checks_passed is False:
        blockers.append("COMPUTER_USE_PERMISSION_CHECK_FAILED")
    if commit_match is False:
        blockers.append("COMPUTER_USE_EVIDENCE_COMMIT_MISMATCH")

    blockers = _unique(blockers)
    evidence_valid_for_live = (
        evidence is not None
        and validation is not None
        and validation.valid
        and evidence.status.value == "pass"
        and platform == current_platform
        and live_requested
        and provider_match is True
        and backend_match is True
        and driver_ready is not False
        and permission_checks_passed is True
        and commit_match is not False
        and raw_screenshot_ok
        and not blockers
    )
    status = _status_from(blockers=blockers, evidence=evidence)
    if evidence_valid_for_live:
        status = CapabilityStatus.PASS
    return PlatformCapabilityResolution(
        platform=platform,  # type: ignore[arg-type]
        status=status,
        live_enabled=evidence_valid_for_live,
        public_live_claim_allowed=False,
        fail_closed=not evidence_valid_for_live,
        reason_code=_reason_code(platform, evidence_valid_for_live),
        blockers=blockers,
        warnings=warnings,
        execution_modes=_execution_modes(evidence_valid_for_live),
        evidence=evidence_source,
        config_hash_match=None,
        commit_match=commit_match,
        provider_match=provider_match,
        backend_match=backend_match,
        driver_ready=driver_ready,
        driver_reason_code=driver_reason_code,
        permission_checks_passed=permission_checks_passed,
        raw_screenshot_persistence_allowed=False,
    )


def _evidence_source(
    *,
    validation: QualificationEvidenceValidation,
    path: str | None,
    checked_at: str,
) -> EvidenceSource:
    if validation.evidence is None:
        return EvidenceSource(
            path=path,
            load_status=EvidenceLoadStatus.INVALID,
            validation_status=validation.status,
            reason_code="COMPUTER_USE_EVIDENCE_INVALID_SCHEMA",
            checked_at=checked_at,
        )
    if validation.valid:
        return EvidenceSource(
            path=path,
            load_status=EvidenceLoadStatus.VALID,
            validation_status=validation.status,
            reason_code=None,
            checked_at=checked_at,
        )
    return EvidenceSource(
        path=path,
        load_status=EvidenceLoadStatus.INVALID,
        validation_status=validation.status,
        reason_code=_mapped_reasons(validation.reason_codes)[0],
        checked_at=checked_at,
    )


def _mapped_reasons(reasons: list[str]) -> list[str]:
    mapped = [EVIDENCE_REASON_MAP.get(reason, reason) for reason in reasons]
    return _unique(mapped)


def _status_from(
    *,
    blockers: list[str],
    evidence: QualificationEvidence | None,
) -> CapabilityStatus:
    if "COMPUTER_USE_RAW_SCREENSHOT_INVARIANT_FAILED" in blockers:
        return CapabilityStatus.FAIL
    if evidence is not None and evidence.status.value == "fail":
        return CapabilityStatus.FAIL
    if blockers:
        return CapabilityStatus.BLOCKED
    return CapabilityStatus.PASS


def _aggregate_status(
    platforms: dict[str, PlatformCapabilityResolution],
) -> CapabilityStatus:
    if any(platform.status == CapabilityStatus.FAIL for platform in platforms.values()):
        return CapabilityStatus.FAIL
    if any(platform.status == CapabilityStatus.BLOCKED for platform in platforms.values()):
        return CapabilityStatus.BLOCKED
    return CapabilityStatus.PASS


def _execution_modes(live_enabled: bool) -> list[PlatformLiveMode]:
    modes = [
        PlatformLiveMode.DISABLED,
        PlatformLiveMode.DRY_RUN,
        PlatformLiveMode.STEP_APPROVAL,
    ]
    if live_enabled:
        modes.append(PlatformLiveMode.SUPERVISED_QUALIFICATION)
    return modes


def _reason_code(platform: str, live_enabled: bool) -> str:
    if live_enabled:
        return "COMPUTER_USE_SUPERVISED_QUALIFICATION_READY"
    return PLATFORM_REASON_CODES[platform]


def _live_requested(config: ComputerUseRuntimeConfig, platform: str) -> bool:
    return (
        config.enabled
        and config.vision_enabled
        and _expected_provider(config, platform) != "none"
        and bool(getattr(config, f"{platform}_live_enabled"))
        and _capture_backend(config, platform) != "disabled"
        and _input_backend(config, platform) != "disabled"
        and config.macos_require_step_approval
    )


def _expected_provider(config: ComputerUseRuntimeConfig, platform: str) -> str:
    del platform
    return config.vision_provider


def _capture_backend(config: ComputerUseRuntimeConfig, platform: str) -> str:
    return str(getattr(config, f"{platform}_capture_backend"))


def _input_backend(config: ComputerUseRuntimeConfig, platform: str) -> str:
    return str(getattr(config, f"{platform}_input_backend"))


def _provider_match(
    evidence: QualificationEvidence | None,
    config: ComputerUseRuntimeConfig,
) -> bool | None:
    if evidence is None:
        return None
    if evidence.provider.name != config.vision_provider:
        return False
    return evidence.provider.name == "none" or evidence.provider.model == config.vision_model


def _backend_match(
    evidence: QualificationEvidence | None,
    config: ComputerUseRuntimeConfig,
    platform: str,
) -> bool | None:
    if evidence is None:
        return None
    return (
        evidence.backends.capture == _capture_backend(config, platform)
        and evidence.backends.input == _input_backend(config, platform)
    )


def _driver_readiness(
    payload: object | None,
    *,
    platform: str,
) -> tuple[bool | None, str | None, list[str]]:
    if payload is None:
        return None, None, []
    try:
        readiness = (
            payload
            if isinstance(payload, PlatformDriverReadiness)
            else PlatformDriverReadiness.model_validate(payload)
        )
    except ValidationError:
        reason_code = "COMPUTER_USE_DRIVER_READINESS_INVALID"
        return False, reason_code, [reason_code]
    if readiness.platform.strip().lower() != platform:
        reason_code = "COMPUTER_USE_DRIVER_READINESS_PLATFORM_MISMATCH"
        return False, reason_code, [reason_code]
    if readiness.live_execution_enabled:
        return True, readiness.reason_code, []
    reason_code = readiness.reason_code or "COMPUTER_USE_DRIVER_NOT_READY"
    return False, reason_code, [reason_code]


def _permission_checks_passed(evidence: QualificationEvidence | None) -> bool | None:
    if evidence is None:
        return None
    return (
        evidence.permissions.screen_recording == "granted"
        and evidence.permissions.accessibility == "granted"
    )


def _commit_match(
    evidence: QualificationEvidence | None,
    current_commit: str | None,
) -> bool | None:
    if evidence is None or not current_commit:
        return None
    return evidence.source_commit == current_commit


def _raw_screenshot_ok(
    config: ComputerUseRuntimeConfig,
    evidence: QualificationEvidence | None,
) -> bool:
    config_ok = (
        config.raw_screenshot_persistence is False
        and config.raw_screenshot_retention == "disabled"
        and config.raw_screenshot_max_count == 0
    )
    if evidence is None:
        return config_ok
    return (
        config_ok
        and evidence.safety.raw_screenshot_persistence is False
        and evidence.safety.raw_screenshot_count == 0
    )


def _normalize_current_platform(value: str) -> Literal["macos", "windows", "linux", "unknown"]:
    normalized = value.strip().lower()
    if normalized in {"macos", "windows", "linux"}:
        return normalized  # type: ignore[return-value]
    return "unknown"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
