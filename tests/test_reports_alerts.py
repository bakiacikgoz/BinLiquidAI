from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.control_plane.reports import build_reports_alerts_logs_manifest
from binliquid.control_plane.snapshot import build_control_plane_snapshot

runner = CliRunner()


def test_reports_alerts_logs_manifest_writes_outputs(tmp_path: Path) -> None:
    snapshot = build_control_plane_snapshot(
        root_dir=tmp_path / "cp",
        profile="lite",
        evidence_root=tmp_path / "artifacts",
    )

    manifest = build_reports_alerts_logs_manifest(
        snapshot=snapshot,
        output_dir=tmp_path / "reports",
    )

    assert manifest.version == "control-plane.report-manifest/v1"
    assert manifest.reports
    assert manifest.logs_export_ref is not None
    assert Path(manifest.logs_export_ref).exists()
    assert (tmp_path / "reports" / "manifest.json").exists()


def test_reports_alerts_logs_cli_manifest(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "control-plane",
            "reports",
            "manifest",
            "--profile",
            "lite",
            "--root-dir",
            str(tmp_path / "cp"),
            "--evidence-root",
            str(tmp_path / "artifacts"),
            "--output-dir",
            str(tmp_path / "reports"),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "control-plane.report-manifest/v1"
    assert payload["logsExportRef"]
