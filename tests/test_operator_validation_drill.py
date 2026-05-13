from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_operator_validation_drill.py"
SPEC = importlib.util.spec_from_file_location("run_operator_validation_drill", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CommandResult = MODULE.CommandResult
ATTESTATION_SCHEMA_VERSION = MODULE.ATTESTATION_SCHEMA_VERSION
run_validation = MODULE.run_validation


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _prepare_root(root: Path) -> None:
    closure_manifest = (
        root
        / "artifacts/release-pack/0.4.1-hat-a-closure-2026-05-13"
        / "release_pack_closure_manifest.json"
    )
    _write_json(
        closure_manifest,
        {
            "status": {
                "macos_desktop_release": "blocked_external_credentials",
                "windows_desktop_release": "blocked_external_credentials",
            },
            "no_ship": {"hat_a_closure": []},
        },
    )
    _write_json(
        root / "artifacts/readiness/2026-05-13/managed_kms_adapter_drill/summary.json",
        {"status": "pass", "report_verified": True},
    )
    _write_json(
        root
        / "artifacts/readiness/2026-05-13/managed_kms_adapter_drill/managed_kms_live_drill.json",
        {"data": {"secret_material_persisted_in_evidence": False}},
    )
    for name in (
        "operator-panel-macos-internal-unsigned-binary-arm64/macos-internal-unsigned-arm64.json",
        "operator-panel-macos-internal-unsigned-binary-x86_64/macos-internal-unsigned-x86_64.json",
        "operator-panel-windows-internal-unsigned-binary-x64/windows-internal-unsigned-x64.json",
    ):
        _write_json(
            root
            / "artifacts/readiness/2026-05-13/operator_panel_internal_unsigned_25814422248"
            / name,
            {"status": "internal_unsigned"},
        )
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs/RELEASE_CHECKLIST.md").write_text("# checklist\n", encoding="utf-8")
    (root / "docs/RELEASE_NOTES_HAT_A_CLOSURE_2026-05-13.md").write_text(
        "# notes\n",
        encoding="utf-8",
    )


def test_operator_validation_proxy_report_passes_without_human_attestation(
    tmp_path: Path,
) -> None:
    _prepare_root(tmp_path)

    def runner(spec):
        stdout = "0.4.1\n" if not spec.expect_json else "{}\n"
        return CommandResult(
            name=spec.name,
            args=spec.args,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    report = run_validation(
        output_root=tmp_path / "out",
        root=tmp_path,
        command_runner=runner,
    )

    assert report["status"] == "pass"
    assert report["validation_scope"] == "operator_proxy_dry_run"
    assert report["operator_attestation"]["non_developer_operator_validated"] is False
    assert (tmp_path / "out" / "operator_validation_report.json").exists()
    assert (tmp_path / "out" / "OPERATOR_VALIDATION_REPORT.md").exists()


def test_operator_validation_attestation_marks_non_developer_scope(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    attestation = tmp_path / "operator_attestation.json"
    _write_json(
        attestation,
        {
            "schema_version": ATTESTATION_SCHEMA_VERSION,
            "operator_name": "Ops User",
            "operator_role": "release_operator",
            "non_developer_operator": True,
            "reviewed_runbook": True,
            "completed_validation": True,
            "validation_report_path": (
                "artifacts/readiness/2026-05-13/operator_validation_drill/"
                "operator_validation_report.json"
            ),
            "release_pack_path": (
                "artifacts/release-pack/0.4.1-hat-a-closure-2026-05-13/"
            ),
            "signed_at_utc": "2026-05-13T18:10:00Z",
        },
    )

    def runner(spec):
        stdout = "0.4.1\n" if not spec.expect_json else "{}\n"
        return CommandResult(
            name=spec.name,
            args=spec.args,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    report = run_validation(
        output_root=tmp_path / "out",
        root=tmp_path,
        command_runner=runner,
        operator_attestation_path=attestation,
    )

    assert report["status"] == "pass"
    assert report["validation_scope"] == "non_developer_operator_attested"
    assert report["operator_attestation"]["non_developer_operator_validated"] is True


def test_operator_validation_rejects_incomplete_attestation(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    attestation = tmp_path / "operator_attestation.json"
    _write_json(
        attestation,
        {
            "schema_version": ATTESTATION_SCHEMA_VERSION,
            "operator_name": "",
            "operator_role": "release_operator",
            "non_developer_operator": True,
            "reviewed_runbook": True,
            "completed_validation": True,
            "validation_report_path": (
                "artifacts/readiness/2026-05-13/operator_validation_drill/"
                "operator_validation_report.json"
            ),
            "release_pack_path": (
                "artifacts/release-pack/0.4.1-hat-a-closure-2026-05-13/"
            ),
            "signed_at_utc": "YYYY-MM-DDTHH:MM:SSZ",
        },
    )

    def runner(spec):
        stdout = "0.4.1\n" if not spec.expect_json else "{}\n"
        return CommandResult(
            name=spec.name,
            args=spec.args,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    report = run_validation(
        output_root=tmp_path / "out",
        root=tmp_path,
        command_runner=runner,
        operator_attestation_path=attestation,
    )

    assert report["status"] == "fail"
    assert report["validation_scope"] == "operator_proxy_dry_run"
    assert report["operator_attestation"]["non_developer_operator_validated"] is False
    assert report["operator_attestation"]["empty_fields"] == ["operator_name"]
    assert report["operator_attestation"]["invalid_fields"] == ["signed_at_utc"]


def test_operator_validation_rejects_unedited_attestation_template(tmp_path: Path) -> None:
    _prepare_root(tmp_path)
    template = ROOT / "docs/templates/non_developer_operator_attestation.template.json"

    def runner(spec):
        stdout = "0.4.1\n" if not spec.expect_json else "{}\n"
        return CommandResult(
            name=spec.name,
            args=spec.args,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    report = run_validation(
        output_root=tmp_path / "out",
        root=tmp_path,
        command_runner=runner,
        operator_attestation_path=template,
    )

    assert report["status"] == "fail"
    assert report["operator_attestation"]["placeholder_fields"] == [
        "notes",
        "operator_name",
        "operator_role",
    ]
    assert report["operator_attestation"]["invalid_fields"] == ["signed_at_utc"]
