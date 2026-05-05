from __future__ import annotations

import json

from typer.testing import CliRunner

from binliquid.cli import app

runner = CliRunner()


def test_computer_use_doctor_reports_all_platforms_without_enabling_live_execution() -> None:
    result = runner.invoke(
        app,
        ["computer-use", "doctor", "--profile", "balanced", "--platform", "all", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["contract_version"] == "2.0"
    assert payload["runtime"] == "computer_use_vision"
    assert set(payload["platforms"]) == {"macos", "windows", "linux"}
    assert payload["platforms"]["windows"]["liveEnabled"] is False
    assert payload["platforms"]["windows"]["reasonCode"] == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    assert payload["platforms"]["linux"]["reasonCode"] == "LINUX_COMPUTER_USE_NOT_QUALIFIED"


def test_computer_use_doctor_can_scope_to_windows() -> None:
    result = runner.invoke(
        app,
        ["computer-use", "doctor", "--profile", "balanced", "--platform", "windows", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload["platforms"]) == {"windows"}
    assert payload["platforms"]["windows"]["stage"] == "not_qualified"


def test_computer_use_qualification_verify_fails_closed_when_report_is_missing(
    tmp_path,
) -> None:
    result = runner.invoke(
        app,
        [
            "computer-use",
            "qualification",
            "verify",
            "--profile",
            "balanced",
            "--platform",
            "windows",
            "--report",
            str(tmp_path / "missing.json"),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["allowed"] is False
    assert "VISION_PLATFORM_QUALIFICATION_MISSING" in payload["blockers"]
