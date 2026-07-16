from __future__ import annotations

import json
from pathlib import Path

from scripts.check_artifact_workspace_compatibility import evaluate_dependency_matrix

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_artifact_dependency_matrix_uses_exact_unique_versions() -> None:
    matrix = json.loads(
        (REPO_ROOT / "contracts/artifact_workspace/dependency_matrix.json").read_text(
            encoding="utf-8"
        )
    )
    packages = matrix["packages"]

    assert matrix["schemaVersion"] == "artifact-workspace.dependency-matrix/v1"
    assert len({item["package"] for item in packages}) == len(packages)
    assert all(item["version"] and item["version"][0].isdigit() for item in packages)
    assert all(not item["version"].startswith(("^", "~", ">", "<", "*")) for item in packages)
    assert {item["package"] for item in packages if item["licenseGate"] == "commercial"} == {
        "handsontable",
        "@handsontable/react-wrapper",
        "tldraw",
    }


def test_artifact_compatibility_probe_fails_closed_on_current_release_blockers() -> None:
    report = evaluate_dependency_matrix(REPO_ROOT)
    reason_codes = {blocker["code"] for blocker in report["blockers"]}

    assert report["matrixValid"] is True
    assert report["releaseReady"] is False
    assert "CSP_DISABLED" in reason_codes
    assert "MISSING_REQUIRED_DEPENDENCY" in reason_codes
    assert "LICENSE_GATE_BLOCKED" in reason_codes
    assert report["canonicalLockfile"] == "pnpm-lock.yaml"
