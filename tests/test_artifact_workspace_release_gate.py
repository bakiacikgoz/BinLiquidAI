from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_artifact_workspace_release_gate import (
    GATE_REPORTS,
    REQUIRED_RELEASE_ARTIFACTS,
    build_release_readiness,
    evaluate_forced_off_license_gate,
)


def _report(candidate: str, *, status: str = "pass", test_count: int = 1) -> dict[str, object]:
    return {
        "schemaVersion": "artifact-workspace-gate/v1",
        "candidateSha": candidate,
        "status": status,
        "testCount": test_count,
        "commands": [],
        "blockingReasons": [],
    }


def test_release_readiness_requires_one_immutable_candidate_and_nonzero_tests() -> None:
    candidate = "a" * 40
    reports = {
        gate: _report(candidate)
        for gate in ("contract", "storage", "rpc", "security", "ui", "e2e", "export")
    }
    reports["license"] = _report(candidate, test_count=2)

    ready = build_release_readiness(candidate, reports, dirty_paths=[])
    assert ready["status"] == "pass"
    assert ready["blockingReasons"] == []
    assert ready["featureFlagDefaults"]["artifact_workspace.enabled"] is False
    assert ready["featureFlagDefaults"]["artifact_workspace.export.enabled"] is False

    reports["e2e"] = _report(candidate, test_count=0)
    blocked = build_release_readiness(candidate, reports, dirty_paths=[])
    assert blocked["status"] == "fail"
    assert "ZERO_TESTS:e2e" in blocked["blockingReasons"]

    reports["e2e"] = _report("b" * 40)
    stale = build_release_readiness(candidate, reports, dirty_paths=[])
    assert "CANDIDATE_MISMATCH:e2e" in stale["blockingReasons"]


def test_license_gate_accepts_only_backend_forced_off_commercial_editors() -> None:
    report = evaluate_forced_off_license_gate(
        {
            "blockers": [
                {"code": "LICENSE_GATE_BLOCKED", "subject": "handsontable"},
                {"code": "LICENSE_GATE_BLOCKED", "subject": "@handsontable/react-wrapper"},
                {"code": "LICENSE_GATE_BLOCKED", "subject": "tldraw"},
            ],
            "matrixValid": True,
        },
        capabilities={"spreadsheet": False, "canvas": False},
    )
    assert report["status"] == "pass"
    assert report["mode"] == "forced_off"

    with pytest.raises(ValueError, match="unexpected license blocker"):
        evaluate_forced_off_license_gate(
            {
                "blockers": [{"code": "CSP_DISABLED", "subject": "tauri.conf.json"}],
                "matrixValid": True,
            },
            capabilities={"spreadsheet": False, "canvas": False},
        )


def test_release_surface_declares_exact_reports_make_targets_and_ci() -> None:
    root = Path(__file__).resolve().parents[1]
    assert set(GATE_REPORTS) == {
        "contract", "storage", "rpc", "security", "ui", "e2e", "export", "license"
    }
    assert set(REQUIRED_RELEASE_ARTIFACTS) == {
        "contract-report.json",
        "storage-integrity-report.json",
        "rpc-performance-report.json",
        "security-report.json",
        "UI_TEST_REPORT.md",
        "export-report.json",
        "license-report.json",
        "release-readiness.json",
        "RELEASE_READINESS.md",
        "NO_SHIP_REGISTER.md",
    }
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    for target in (
        "artifact-contract-gate",
        "artifact-storage-gate",
        "artifact-rpc-gate",
        "artifact-security-gate",
        "artifact-ui-gate",
        "artifact-e2e-gate",
        "artifact-export-gate",
        "artifact-license-gate",
        "artifact-workspace-release-gate",
    ):
        assert f"{target}:" in makefile
    workflow = (root / ".github/workflows/artifact-workspace-ci.yml").read_text(
        encoding="utf-8"
    )
    assert "windows-latest" in workflow
    assert "macos-latest" in workflow
    assert "--gate workspace-release" in workflow
    package = json.loads((root / "apps/operator-panel/package.json").read_text(encoding="utf-8"))
    assert "pass-with-no-tests" not in package["scripts"]["test:e2e"]
