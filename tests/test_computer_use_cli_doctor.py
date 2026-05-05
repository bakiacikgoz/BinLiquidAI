from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.runtime.config import RuntimeConfig

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]


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


def test_computer_use_doctor_macos_shape_reports_exact_fail_closed_blockers() -> None:
    result = runner.invoke(
        app,
        ["computer-use", "doctor", "--profile", "balanced", "--platform", "macos", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["platform"] == "macos"
    assert payload["stage"] == "not_configured"
    assert payload["liveEnabled"] is False
    assert payload["reasonCode"] == "MACOS_LIVE_FLAG_DISABLED"
    assert payload["permissions"]["screenRecording"] in {"granted", "missing", "unknown"}
    assert payload["permissions"]["accessibility"] in {"granted", "missing", "unknown"}
    assert payload["provider"]["ready"] is False
    assert payload["capture"]["backend"] == "disabled"
    assert payload["capture"]["reasonCode"] == "MACOS_CAPTURE_BACKEND_DISABLED"
    assert payload["input"]["backend"] == "disabled"
    assert payload["input"]["reasonCode"] == "MACOS_INPUT_BACKEND_DISABLED"
    assert payload["qualification"]["reasonCode"] == "MACOS_QUALIFICATION_REPORT_MISSING"
    assert payload["safety"]["rawScreenshotPersistence"] is False
    assert payload["safety"]["terminalPolicy"] == "deny"
    assert payload["safety"]["sensitiveSurfacePolicy"] == "stop"


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


def test_computer_use_qualification_verify_accepts_schema_input_fixture() -> None:
    result = runner.invoke(
        app,
        [
            "computer-use",
            "qualification",
            "verify",
            "--schema",
            str(REPO_ROOT / "contracts" / "computer_use" / "platform_qualification.schema.json"),
            "--input",
            str(
                REPO_ROOT
                / "contracts"
                / "computer_use"
                / "fixtures"
                / "windows_platform_qualification_pass_fixture.json"
            ),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["reviewOnly"] is True
    assert payload["runtimeLiveEnabled"] is False
    assert payload["platform"] == "windows"
    assert payload["checks"]["approval_freshness_enforced"] is True
    assert payload["checks"]["replay_integrity_verified"] is True


def test_macos_live_qualification_run_is_opt_in_and_does_not_enable_runtime(tmp_path) -> None:
    output = tmp_path / "macos_qualification_report.json"
    result = runner.invoke(
        app,
        [
            "computer-use",
            "qualification",
            "run",
            "--profile",
            "balanced",
            "--platform",
            "macos",
            "--suite",
            "live-fixture-smoke",
            "--mode",
            "supervised",
            "--output",
            str(output),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "skipped"
    assert report["status"] == "skipped"
    assert report["stage"] == "not_qualified"
    assert report["artifacts"]["rawScreenshotCount"] == 0


def test_all_profiles_keep_computer_use_defaults_fail_closed() -> None:
    for profile in ("balanced", "default", "enterprise", "lite", "research", "restricted"):
        config = RuntimeConfig.from_profile(profile, root_dir=REPO_ROOT).computer_use

        assert config.vision_enabled is False
        assert config.vision_provider == "none"
        assert config.raw_screenshot_persistence is False
        assert config.raw_screenshot_retention == "disabled"
        assert config.raw_screenshot_max_count == 0
        assert config.terminal_control == "deny"
        assert config.sensitive_surface_policy == "stop"
        assert config.macos_live_enabled is False
        assert config.macos_capture_backend == "disabled"
        assert config.windows_live_enabled is False
        assert config.linux_live_enabled is False
