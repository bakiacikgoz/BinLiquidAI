from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

EXPECTED_COMPUTER_USE_REASON = "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), None
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError:
        return None, "invalid_json"


def _bool_value(payload: Mapping[str, Any] | None, key: str) -> bool:
    return bool(payload and payload.get(key) is True)


def _status_value(payload: Mapping[str, Any] | None, key: str) -> str:
    if not payload:
        return "missing"
    value = payload.get(key)
    return str(value).strip().lower() if value is not None else "missing"


def _first_present(payload: Mapping[str, Any] | None, keys: tuple[str, ...]) -> Any:
    if not payload:
        return None
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return None


def _computer_use_capability(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    features = payload.get("features") if payload else None
    if isinstance(features, Mapping):
        capability = features.get("computerUsePilot")
        if isinstance(capability, Mapping):
            return capability
    return {}


def _doctor_reports_failure(payload: Mapping[str, Any] | None) -> bool:
    if not payload:
        return True
    status = _first_present(payload, ("status", "overall_status", "result"))
    if status is None:
        return False
    return str(status).strip().lower() in {"fail", "failed", "error", "red"}


def evaluate_gate(
    *,
    release_status: Mapping[str, Any] | None,
    installer_smoke: Mapping[str, Any] | None,
    operator_capabilities: Mapping[str, Any] | None,
    doctor: Mapping[str, Any] | None,
    evidence: Mapping[str, str] | None = None,
    release_status_error: str | None = None,
    installer_smoke_error: str | None = None,
    operator_capabilities_error: str | None = None,
    doctor_error: str | None = None,
) -> dict[str, Any]:
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    if release_status_error == "missing":
        _add_reason(blocking_reasons, "release_status_missing")
    elif release_status_error == "invalid_json":
        _add_reason(blocking_reasons, "release_status_invalid_json")

    if installer_smoke_error == "missing":
        _add_reason(blocking_reasons, "installer_smoke_missing")
        _add_reason(blocking_reasons, "clean_vm_smoke_missing")
    elif installer_smoke_error == "invalid_json":
        _add_reason(blocking_reasons, "installer_smoke_invalid_json")

    if operator_capabilities_error == "missing":
        _add_reason(blocking_reasons, "operator_capabilities_missing")
    elif operator_capabilities_error == "invalid_json":
        _add_reason(blocking_reasons, "operator_capabilities_invalid_json")

    if doctor_error == "missing":
        _add_reason(blocking_reasons, "doctor_missing")
    elif doctor_error == "invalid_json":
        _add_reason(blocking_reasons, "doctor_invalid_json")

    signed = _bool_value(release_status, "signed")
    timestamped = _bool_value(release_status, "timestamped")
    signtool_verify_status = _status_value(release_status, "signtool_verify_status")

    if not signed:
        _add_reason(blocking_reasons, "artifact_not_signed")
    if not timestamped:
        _add_reason(blocking_reasons, "artifact_not_timestamped")
    if signtool_verify_status != "pass":
        _add_reason(blocking_reasons, "signtool_verify_not_pass")

    clean_vm_claimed = _bool_value(installer_smoke, "clean_vm_claimed")
    run_install_used = _bool_value(installer_smoke, "run_install_used")
    allow_unsigned_smoke_used = _bool_value(installer_smoke, "allow_unsigned_smoke_used")
    installer_signed = _bool_value(installer_smoke, "signed")

    if allow_unsigned_smoke_used:
        _add_reason(blocking_reasons, "unsigned_internal_smoke_not_public_release_eligible")
    if installer_smoke and not installer_signed:
        _add_reason(blocking_reasons, "artifact_not_signed")
    if installer_smoke and (not clean_vm_claimed or not run_install_used):
        _add_reason(blocking_reasons, "clean_vm_smoke_missing")

    installer_status = _status_value(installer_smoke, "install_status")
    bundled_runtime_status = _status_value(installer_smoke, "bundled_runtime_status")
    operator_capabilities_status = _status_value(installer_smoke, "operator_capabilities_status")
    doctor_status = _status_value(installer_smoke, "doctor_status")

    if installer_smoke and installer_status != "pass":
        _add_reason(blocking_reasons, "installer_install_not_pass")
    if installer_smoke and bundled_runtime_status != "pass":
        _add_reason(blocking_reasons, "bundled_runtime_not_pass")
    if installer_smoke and operator_capabilities_status != "pass":
        _add_reason(blocking_reasons, "operator_capabilities_not_pass")
    if installer_smoke and doctor_status != "pass":
        _add_reason(blocking_reasons, "doctor_not_pass")

    capability = _computer_use_capability(operator_capabilities)
    computer_use_enabled = bool(capability.get("enabled") is True)
    computer_use_reason_code = capability.get("reasonCode")
    computer_use_platform = capability.get("platform")
    computer_use_stage = capability.get("stage")

    if computer_use_enabled:
        _add_reason(blocking_reasons, "computer_use_enabled")
    if computer_use_reason_code != EXPECTED_COMPUTER_USE_REASON:
        _add_reason(blocking_reasons, "computer_use_reason_code_mismatch")
    if computer_use_platform not in (None, "windows"):
        _add_reason(blocking_reasons, "computer_use_platform_mismatch")
    if computer_use_stage not in (None, "not_qualified"):
        _add_reason(blocking_reasons, "computer_use_stage_mismatch")

    if _doctor_reports_failure(doctor):
        _add_reason(blocking_reasons, "doctor_not_pass")

    release_hash = _first_present(
        release_status,
        ("installer_sha256", "artifact_sha256", "nsis_sha256"),
    )
    smoke_hash = _first_present(installer_smoke, ("installer_sha256",))
    if release_hash and smoke_hash and str(release_hash).lower() != str(smoke_hash).lower():
        _add_reason(blocking_reasons, "installer_hash_mismatch")

    signed_rc_allowed = (
        release_status_error is None
        and signed
        and timestamped
        and signtool_verify_status == "pass"
    )
    public_release_allowed = len(blocking_reasons) == 0

    if public_release_allowed:
        status = "pass"
    elif any(
        reason in blocking_reasons
        for reason in (
            "computer_use_enabled",
            "computer_use_reason_code_mismatch",
            "computer_use_platform_mismatch",
            "computer_use_stage_mismatch",
            "installer_hash_mismatch",
            "operator_capabilities_invalid_json",
            "doctor_invalid_json",
            "release_status_invalid_json",
            "installer_smoke_invalid_json",
        )
    ):
        status = "fail"
    else:
        status = "blocked"

    return {
        "artifact_type": str(release_status.get("artifact_type", "nsis"))
        if release_status
        else "nsis",
        "blocking_reasons": blocking_reasons,
        "bundled_runtime_status": bundled_runtime_status,
        "clean_vm_smoke_status": "pass"
        if clean_vm_claimed and run_install_used and installer_status == "pass"
        else "blocked",
        "computer_use_live_enabled": computer_use_enabled,
        "computer_use_reason_code": computer_use_reason_code,
        "doctor_status": doctor_status,
        "evidence": dict(evidence or {}),
        "installer_smoke_status": installer_status,
        "operator_capabilities_status": operator_capabilities_status,
        "platform": "windows",
        "public_release_allowed": public_release_allowed,
        "signed": signed,
        "signed_rc_allowed": signed_rc_allowed,
        "signtool_verify_status": signtool_verify_status,
        "status": status,
        "timestamped": timestamped,
        "warnings": warnings,
    }


def evaluate_from_files(args: argparse.Namespace) -> dict[str, Any]:
    release_status, release_error = load_json(args.release_status)
    installer_smoke, installer_error = load_json(args.installer_smoke)
    operator_capabilities, capabilities_error = load_json(args.operator_capabilities)
    doctor, doctor_error = load_json(args.doctor)

    evidence = {
        "doctor": str(args.doctor),
        "installer_smoke": str(args.installer_smoke),
        "operator_capabilities": str(args.operator_capabilities),
        "release_status": str(args.release_status),
    }
    if args.runtime_manifest:
        evidence["runtime_manifest"] = str(args.runtime_manifest)
    if args.bundle_hashes:
        evidence["bundle_hashes"] = str(args.bundle_hashes)

    return evaluate_gate(
        release_status=release_status,
        installer_smoke=installer_smoke,
        operator_capabilities=operator_capabilities,
        doctor=doctor,
        evidence=evidence,
        release_status_error=release_error,
        installer_smoke_error=installer_error,
        operator_capabilities_error=capabilities_error,
        doctor_error=doctor_error,
    )


def write_gate_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Windows public release gate evidence.")
    parser.add_argument("--release-status", required=True, type=Path)
    parser.add_argument("--installer-smoke", required=True, type=Path)
    parser.add_argument("--operator-capabilities", required=True, type=Path)
    parser.add_argument("--doctor", required=True, type=Path)
    parser.add_argument("--runtime-manifest", type=Path)
    parser.add_argument("--bundle-hashes", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fail-on-blocked", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    report = evaluate_from_files(args)
    write_gate_report(args.output, report)
    if args.fail_on_blocked and not report["public_release_allowed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
