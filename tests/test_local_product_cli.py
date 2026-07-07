from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
from scripts.run_local_product_readiness_gate import run_local_product_readiness_gate


def test_local_product_cli_matrix_reports_not_evidenced_targets() -> None:
    result = CliRunner().invoke(app, ["local-product", "matrix", "--json"])

    assert result.exit_code == 0, result.stdout
    assert '"schemaVersion": "local_product_readiness_matrix/v1"' in result.stdout
    assert '"notEvidencedTargets"' in result.stdout


def test_local_product_readiness_script_writes_artifacts(tmp_path: Path) -> None:
    report = run_local_product_readiness_gate(
        profile="enterprise",
        target_value="windows-x64",
        matrix=False,
        output_root=tmp_path,
        json_output=True,
        run_product_closure=False,
    )

    assert report["schemaVersion"] == "local_product_readiness/v1"
    assert report["target"]["targetId"] == "windows-x64"
    assert (tmp_path / "windows-x64" / "local_product_readiness_report.json").exists()
    assert report["rawPromptPersisted"] is False
    assert report["liveComputerUseEnabled"] is False

