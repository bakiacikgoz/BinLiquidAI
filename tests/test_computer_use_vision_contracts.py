from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.contracts.operator_panel import OperatorCapabilitiesPayload
from binliquid.runtime.platform import current_platform

runner = CliRunner()


def test_operator_capabilities_exposes_additive_vision_runtime_contract() -> None:
    result = runner.invoke(app, ["operator", "capabilities", "--json"])

    assert result.exit_code == 0
    payload = OperatorCapabilitiesPayload.model_validate_json(result.stdout)
    vision = payload.features.computer_use_vision_runtime

    assert vision.replayable is True
    assert vision.fail_closed is True
    assert vision.scope == "vision_first_desktop_web_file"
    assert set(vision.execution_modes).issubset({"dry_run", "step_approval", "execute"})

    if current_platform().label == "windows":
        assert vision.enabled is False
        assert vision.stage == "not_qualified"
        assert vision.reason_code == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    else:
        assert vision.enabled is False
        assert vision.stage in {"not_configured", "configured", "not_qualified"}


def test_operator_capabilities_schema_contains_vision_runtime_field() -> None:
    result = runner.invoke(app, ["operator", "capabilities", "--json"])
    assert result.exit_code == 0
    raw = json.loads(result.stdout)

    assert "computerUsePilot" in raw["features"]
    assert "computerUseVisionRuntime" in raw["features"]
    assert raw["features"]["computerUseVisionRuntime"]["failClosed"] is True


def test_cli_vision_first_runtime_fails_closed_without_provider(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "computer-use",
            "run",
            "--once",
            "Read the current screen",
            "--runtime",
            "vision-first",
            "--job-id",
            "vision-cli",
            "--root-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["computer_use"]["status"] == "failed"
    assert payload["computer_use"]["stop_reason"] == "VISION_RUNTIME_NOT_CONFIGURED"
    assert payload["computer_use"]["redaction_report"]["raw_screenshot_persisted_count"] == 0
