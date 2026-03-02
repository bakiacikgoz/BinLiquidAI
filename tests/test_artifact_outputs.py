from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app

runner = CliRunner()


def test_cli_doctor_creates_artifact_scaffold(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def fake_status(**_: object):
        return {
            "selected_provider": "transformers",
            "primary": {"daemon_ok": False, "model_present": False},
            "secondary": {"runtime_available": True},
        }

    monkeypatch.setattr("binliquid.cli.check_provider_chain", fake_status)
    result = runner.invoke(app, ["doctor", "--profile", "lite"])

    assert result.exit_code == 0
    root = tmp_path / "artifacts"
    assert (root / "status.json").exists()
    assert (root / "test_summary.json").exists()
    assert (root / "benchmark_summary.json").exists()
    assert (root / "router_shadow_summary.json").exists()
    assert (root / "research_summary.json").exists()
    assert (root / "governance_summary.json").exists()


def test_cli_benchmark_updates_benchmark_summary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    def fake_bench(**_: object):
        return {"results": {"A": {"success_rate": 1.0}}, "output_path": "x.json"}

    monkeypatch.setattr("binliquid.cli.run_smoke_benchmark", fake_bench)
    result = runner.invoke(app, ["benchmark", "smoke", "--mode", "A"])

    assert result.exit_code == 0
    summary = json.loads((tmp_path / "artifacts" / "benchmark_summary.json").read_text())
    assert summary["artifact"] == "benchmark_summary"
    assert summary["status"] == "ok"
