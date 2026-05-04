from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "evaluate_windows_release_gate.py"

spec = importlib.util.spec_from_file_location("evaluate_windows_release_gate", SCRIPT_PATH)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

DEFAULT = object()


def release_status(**overrides):
    payload = {
        "artifact_type": "nsis",
        "installer_sha256": "a" * 64,
        "platform": "windows",
        "signed": True,
        "signtool_verify_status": "pass",
        "status": "signed_verified_external_smoke_required",
        "timestamped": True,
    }
    payload.update(overrides)
    return payload


def installer_smoke(**overrides):
    payload = {
        "allow_unsigned_smoke_used": False,
        "bundled_runtime_status": "pass",
        "clean_vm_claimed": True,
        "computer_use_live_enabled": False,
        "computer_use_reason_code": "WINDOWS_COMPUTER_USE_NOT_QUALIFIED",
        "doctor_status": "pass",
        "install_status": "pass",
        "installer_sha256": "a" * 64,
        "operator_capabilities_status": "pass",
        "platform": "windows",
        "run_install_used": True,
        "signed": True,
    }
    payload.update(overrides)
    return payload


def operator_capabilities(**overrides):
    computer_use = {
        "enabled": False,
        "failClosed": True,
        "platform": "windows",
        "reasonCode": "WINDOWS_COMPUTER_USE_NOT_QUALIFIED",
        "stage": "not_qualified",
    }
    computer_use.update(overrides)
    return {"features": {"computerUsePilot": computer_use}}


def doctor(**overrides):
    payload = {"status": "degraded_fallback"}
    payload.update(overrides)
    return payload


def evaluate(
    release=DEFAULT,
    smoke=DEFAULT,
    capabilities=DEFAULT,
    doctor_payload=DEFAULT,
    **errors,
):
    return gate.evaluate_gate(
        release_status=release_status() if release is DEFAULT else release,
        installer_smoke=installer_smoke() if smoke is DEFAULT else smoke,
        operator_capabilities=operator_capabilities() if capabilities is DEFAULT else capabilities,
        doctor=doctor() if doctor_payload is DEFAULT else doctor_payload,
        **errors,
    )


def assert_blocked(report, reason: str):
    assert report["public_release_allowed"] is False
    assert reason in report["blocking_reasons"]


def test_all_evidence_pass_allows_public_release():
    report = evaluate()

    assert report["status"] == "pass"
    assert report["signed_rc_allowed"] is True
    assert report["public_release_allowed"] is True
    assert report["blocking_reasons"] == []


def test_signing_missing_blocks_public_release():
    report = evaluate(release=release_status(signed=False))

    assert_blocked(report, "artifact_not_signed")
    assert report["signed_rc_allowed"] is False


def test_timestamp_missing_blocks_public_release():
    report = evaluate(release=release_status(timestamped=False))

    assert_blocked(report, "artifact_not_timestamped")
    assert report["signed_rc_allowed"] is False


def test_signtool_verify_fail_blocks_public_release():
    report = evaluate(release=release_status(signtool_verify_status="fail"))

    assert_blocked(report, "signtool_verify_not_pass")
    assert report["signed_rc_allowed"] is False


def test_clean_vm_smoke_missing_blocks_public_but_keeps_signed_rc_allowed():
    report = evaluate(
        smoke=None,
        installer_smoke_error="missing",
    )

    assert_blocked(report, "clean_vm_smoke_missing")
    assert report["signed_rc_allowed"] is True


def test_unsigned_internal_smoke_is_not_public_release_eligible():
    report = evaluate(
        smoke=installer_smoke(
            allow_unsigned_smoke_used=True,
            signed=False,
        )
    )

    assert_blocked(report, "unsigned_internal_smoke_not_public_release_eligible")
    assert report["signed_rc_allowed"] is True


def test_runtime_status_fail_blocks_public_release():
    report = evaluate(smoke=installer_smoke(bundled_runtime_status="fail"))

    assert_blocked(report, "bundled_runtime_not_pass")


def test_operator_capabilities_status_fail_blocks_public_release():
    report = evaluate(smoke=installer_smoke(operator_capabilities_status="fail"))

    assert_blocked(report, "operator_capabilities_not_pass")


def test_doctor_fail_blocks_public_release():
    report = evaluate(doctor_payload=doctor(status="fail"))

    assert_blocked(report, "doctor_not_pass")


def test_computer_use_enabled_is_hard_fail():
    report = evaluate(capabilities=operator_capabilities(enabled=True))

    assert report["status"] == "fail"
    assert_blocked(report, "computer_use_enabled")


def test_wrong_computer_use_reason_code_is_hard_fail():
    report = evaluate(capabilities=operator_capabilities(reasonCode="MACOS_COMPUTER_USE_PILOT"))

    assert report["status"] == "fail"
    assert_blocked(report, "computer_use_reason_code_mismatch")


def test_operator_capabilities_missing_blocks_public_release():
    report = evaluate(capabilities=None, operator_capabilities_error="missing")

    assert_blocked(report, "operator_capabilities_missing")


def test_installer_hash_mismatch_blocks_public_release():
    report = evaluate(smoke=installer_smoke(installer_sha256="b" * 64))

    assert report["status"] == "fail"
    assert_blocked(report, "installer_hash_mismatch")


def test_malformed_json_is_reported_as_blocked(tmp_path):
    release_path = tmp_path / "windows-release-status.json"
    smoke_path = tmp_path / "windows-installer-smoke.json"
    capabilities_path = tmp_path / "operator_capabilities.json"
    doctor_path = tmp_path / "doctor_balanced.json"
    output_path = tmp_path / "windows-public-release-gate.json"

    release_path.write_text(json.dumps(release_status()), encoding="utf-8")
    smoke_path.write_text(json.dumps(installer_smoke()), encoding="utf-8")
    capabilities_path.write_text("{not-json", encoding="utf-8")
    doctor_path.write_text(json.dumps(doctor()), encoding="utf-8")

    report = gate.evaluate_from_files(
        SimpleNamespace(
            bundle_hashes=None,
            doctor=doctor_path,
            installer_smoke=smoke_path,
            operator_capabilities=capabilities_path,
            output=output_path,
            release_status=release_path,
            runtime_manifest=None,
        )
    )

    assert report["status"] == "fail"
    assert_blocked(report, "operator_capabilities_invalid_json")


def test_windows_powershell_utf8_bom_json_is_accepted(tmp_path):
    release_path = tmp_path / "windows-release-status.json"
    smoke_path = tmp_path / "windows-installer-smoke.json"
    capabilities_path = tmp_path / "operator_capabilities.json"
    doctor_path = tmp_path / "doctor_balanced.json"
    output_path = tmp_path / "windows-public-release-gate.json"

    release_path.write_text(json.dumps(release_status()), encoding="utf-8-sig")
    smoke_path.write_text(json.dumps(installer_smoke()), encoding="utf-8-sig")
    capabilities_path.write_text(json.dumps(operator_capabilities()), encoding="utf-8-sig")
    doctor_path.write_text(json.dumps(doctor()), encoding="utf-8-sig")

    report = gate.evaluate_from_files(
        SimpleNamespace(
            bundle_hashes=None,
            doctor=doctor_path,
            installer_smoke=smoke_path,
            operator_capabilities=capabilities_path,
            output=output_path,
            release_status=release_path,
            runtime_manifest=None,
        )
    )

    assert report["public_release_allowed"] is True
