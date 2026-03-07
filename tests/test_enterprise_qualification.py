from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.enterprise.maintenance import ga_readiness_report
from binliquid.enterprise.qualification import (
    MIN_GREEN_SOAK_SECONDS,
    evaluate_qualification_evidence,
    run_qualification,
    write_qualification_report,
)
from binliquid.enterprise.signing import (
    canonical_payload_hash,
    verify_signed_artifact,
    write_signed_json,
)
from binliquid.runtime.config import RuntimeConfig
from binliquid.team.pilot_gate import build_deterministic_pilot_orchestrator

runner = CliRunner()


def _write_signing_material(
    root: Path,
    *,
    key_id: str = "enterprise-signing-current",
) -> dict[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes_raw()
    public_raw = private_key.public_key().public_bytes_raw()

    private_dir = root / ".binliquid" / "keys" / "private"
    trusted_dir = root / ".binliquid" / "keys" / "trusted"
    private_dir.mkdir(parents=True, exist_ok=True)
    trusted_dir.mkdir(parents=True, exist_ok=True)

    private_payload = {
        "schema_version": "1",
        "key_id": key_id,
        "algorithm": "ed25519",
        "purpose": "artifact-signing",
        "private_key": base64.b64encode(private_raw).decode("ascii"),
        "public_key": base64.b64encode(public_raw).decode("ascii"),
        "created_at": datetime.now(UTC).isoformat(),
    }
    public_payload = {
        "schema_version": "1",
        "key_id": key_id,
        "algorithm": "ed25519",
        "purpose": "artifact-signing",
        "public_key": base64.b64encode(public_raw).decode("ascii"),
        "state": "active",
        "created_at": datetime.now(UTC).isoformat(),
    }
    manifest = {"schema_version": "1", "current_key_id": key_id, "revoked_keys": []}

    (private_dir / "current_key.json").write_text(
        json.dumps(private_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (trusted_dir / f"{key_id}.json").write_text(
        json.dumps(public_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    ((root / ".binliquid" / "keys") / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "key_id": key_id,
        "private_key": base64.b64encode(private_raw).decode("ascii"),
    }


def _write_identity_assertion(
    root: Path,
    signing_material: dict[str, str],
    *,
    permissions: list[str],
) -> None:
    payload = {
        "schema_version": "1",
        "assertion_type": "external",
        "actor_id": "alice",
        "subject": "alice@example.com",
        "issuer": "idp.example.local",
        "roles": ["platform_admin", "security_admin"],
        "permissions": permissions,
        "issued_at": datetime.now(UTC).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
        "key_id": signing_material["key_id"],
    }
    signature = Ed25519PrivateKey.from_private_bytes(
        base64.b64decode(signing_material["private_key"])
    ).sign(canonical_payload_hash(payload).encode("utf-8"))
    payload["signature"] = base64.b64encode(signature).decode("ascii")
    identity_dir = root / ".binliquid" / "identity"
    identity_dir.mkdir(parents=True, exist_ok=True)
    (identity_dir / "current_assertion.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_enterprise_docs(root: Path) -> None:
    for name in (
        "SECURITY_BASELINE.md",
        "KEY_MANAGEMENT.md",
        "UPGRADE_AND_RECOVERY.md",
        "OBSERVABILITY_AND_SLO.md",
        "QUALIFICATION_MATRIX.md",
        "INSTALL.md",
        "DEPLOYMENT_GUIDE.md",
        "SUPPORT_BUNDLE.md",
    ):
        (root / name).write_text(f"# {name}\n", encoding="utf-8")


def _green_workload(name: str, *, duration_seconds: int) -> dict[str, object]:
    return {
        "name": name,
        "purpose": name,
        "start_time": datetime.now(UTC).isoformat(),
        "end_time": datetime.now(UTC).isoformat(),
        "duration_seconds": duration_seconds,
        "execution_mode": "mixed",
        "required_for_green": name != "24h_soak_flow",
        "support_classification": "supported",
        "pass_fail": "pass",
        "task_count_total": 4,
        "task_count_success": 4,
        "task_count_failed": 0,
        "failure_class_breakdown": {},
        "replay_verify_status": "pass",
        "signing_verify_status": "pass",
        "approval_latency_summary": {"count": 1},
        "provider_retry_count": 0,
        "stale_approval_count": 0,
        "stale_resume_count": 0,
        "resume_duplicate_suppressed_count": 0,
        "memory_conflict_count": 0,
        "serialized_due_to_policy_count": 0,
        "fallback_mode_count": 0,
        "operator_intervention_count": 0,
        "support_bundle_sufficient": True,
        "metrics_snapshot_sufficient": True,
        "unclear_errors": [],
        "runbook_gaps": [],
        "notes": [],
        "operational_followups": [],
        "artifacts": {},
        "blocking_findings": [],
        "residual_risks": [],
        "evidence_verified": True,
    }


def _complete_green_qualification_payload() -> dict[str, object]:
    workloads = [
        _green_workload("baseline_enterprise_flow", duration_seconds=300),
        _green_workload("approval_heavy_flow", duration_seconds=300),
        _green_workload("conflict_heavy_flow", duration_seconds=300),
        _green_workload("soak_6h_flow", duration_seconds=MIN_GREEN_SOAK_SECONDS),
        _green_workload("failure_injection_flow", duration_seconds=300),
        {
            **_green_workload("24h_soak_flow", duration_seconds=0),
            "required_for_green": False,
            "pass_fail": "not_run",
            "replay_verify_status": "not_run",
            "signing_verify_status": "not_run",
            "evidence_verified": False,
        },
    ]
    evaluation = evaluate_qualification_evidence(
        qualification_payload={
            "profile": "enterprise",
            "workloads": workloads,
            "minimum_green_soak_seconds": MIN_GREEN_SOAK_SECONDS,
        }
    )
    return {
        "version": "1",
        "generated_at": datetime.now(UTC).isoformat(),
        "runtime_version": "test",
        "environment_summary": {"platform": "test"},
        "profile": "enterprise",
        "signing_mode": "local_file",
        "identity_mode": "external_assertion",
        "qualification_evidence_mode": "mixed",
        "minimum_green_soak_seconds": MIN_GREEN_SOAK_SECONDS,
        "qualification_status": evaluation["qualification_status"],
        "workloads": workloads,
        "supported_profiles": evaluation["supported_profiles"],
        "conditional_profiles": evaluation["conditional_profiles"],
        "unsupported_profiles": evaluation["unsupported_profiles"],
        "blocking_findings": evaluation["blocking_findings"],
        "residual_risks": [
            item
            for item in evaluation["residual_risks"]
            if item != "24h soak evidence not yet published"
        ],
        "recommended_status": evaluation["recommended_status"],
        "go_no_go": evaluation["go_no_go"],
        "operational_findings": evaluation["operational_findings"],
        "artifacts": {},
    }


def test_qualification_runner_writes_signed_report(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _write_signing_material(tmp_path)
    config = RuntimeConfig.from_profile("enterprise")

    payload = run_qualification(
        config=config,
        mode="mixed",
        soak_hours=0.0003,
        output_root=tmp_path / "artifacts" / "qualification",
        live_orchestrator_builder=build_deterministic_pilot_orchestrator,
    )
    paths = write_qualification_report(
        payload=payload,
        config=config,
        output_root=tmp_path / "artifacts" / "qualification",
    )

    verify = verify_signed_artifact(path=paths["latest_json"], config=config)
    assert verify["verified"] is True
    assert Path(paths["run_markdown"]).exists()
    assert payload["qualification_status"] == "partial"
    assert {item["name"] for item in payload["workloads"]} >= {
        "baseline_enterprise_flow",
        "approval_heavy_flow",
        "conflict_heavy_flow",
        "soak_6h_flow",
        "failure_injection_flow",
    }


def test_ga_readiness_uses_signed_qualification_evidence(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _write_signing_material(tmp_path)
    _write_enterprise_docs(tmp_path)
    config = RuntimeConfig.from_profile("enterprise")

    payload = run_qualification(
        config=config,
        mode="mixed",
        soak_hours=0.0003,
        output_root=tmp_path / "artifacts" / "qualification",
        live_orchestrator_builder=build_deterministic_pilot_orchestrator,
    )
    write_qualification_report(
        payload=payload,
        config=config,
        output_root=tmp_path / "artifacts" / "qualification",
    )

    readiness = ga_readiness_report(config)
    assert readiness["overall_status"] == "yellow"
    assert readiness["go_no_go"] == "conditional"
    assert readiness["qualification_report"]["verified"] is True
    assert readiness["qualification_report"]["minimum_green_soak_seconds"] == MIN_GREEN_SOAK_SECONDS


def test_ga_readiness_turns_green_with_complete_verified_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_signing_material(tmp_path)
    _write_enterprise_docs(tmp_path)
    config = RuntimeConfig.from_profile("enterprise")
    payload = _complete_green_qualification_payload()

    write_signed_json(
        path=tmp_path / "artifacts" / "qualification_report.json",
        artifact="qualification_report",
        data=payload,
        config=config,
        purpose="qualification-report",
        status="ok",
    )

    readiness = ga_readiness_report(config)
    assert readiness["overall_status"] == "green"
    assert readiness["go_no_go"] == "go"
    assert readiness["qualification_report"]["verified"] is True


def test_ga_readiness_red_on_invalid_qualification_signature(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _write_signing_material(tmp_path)
    _write_enterprise_docs(tmp_path)
    config = RuntimeConfig.from_profile("enterprise")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "qualification_report.json").write_text(
        json.dumps({"artifact": "qualification_report", "data": {"bad": True}}, ensure_ascii=False),
        encoding="utf-8",
    )

    readiness = ga_readiness_report(config)
    assert readiness["overall_status"] == "red"
    assert readiness["go_no_go"] == "no-go"
    assert readiness["qualification_report"]["verified"] is False


def test_cli_qualification_run_generates_reports(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    signing = _write_signing_material(tmp_path)
    _write_identity_assertion(
        tmp_path,
        signing,
        permissions=[
            "runtime.run",
            "approval.decide",
            "approval.execute",
            "support.export",
            "backup.create",
            "restore.verify",
        ],
    )

    monkeypatch.setattr(
        "binliquid.cli._build_orchestrator",
        lambda config, **kwargs: build_deterministic_pilot_orchestrator(config),
    )

    result = runner.invoke(
        app,
        [
            "qualification",
            "run",
            "--profile",
            "enterprise",
            "--mode",
            "mixed",
            "--soak-hours",
            "0.0003",
            "--output-root",
            "artifacts/qualification",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["go_no_go"] == "conditional"
    assert (tmp_path / "artifacts" / "qualification_report.json").exists()
    assert (tmp_path / "artifacts" / "QUALIFICATION_REPORT.md").exists()


def test_qualification_runner_captures_workload_failure(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    _write_signing_material(tmp_path)
    config = RuntimeConfig.from_profile("enterprise")

    def fail_baseline(**kwargs):  # noqa: ANN003
        raise RuntimeError("baseline exploded")

    monkeypatch.setattr(
        "binliquid.enterprise.qualification._run_baseline_enterprise_flow",
        fail_baseline,
    )

    payload = run_qualification(
        config=config,
        mode="mixed",
        soak_hours=0.0003,
        output_root=tmp_path / "artifacts" / "qualification",
        live_orchestrator_builder=build_deterministic_pilot_orchestrator,
    )

    baseline = next(
        item for item in payload["workloads"] if item["name"] == "baseline_enterprise_flow"
    )
    assert baseline["pass_fail"] == "fail"
    assert baseline["blocking_findings"] == ["QUALIFICATION_WORKLOAD_FAILED"]
    assert payload["qualification_status"] in {"partial", "fail"}
