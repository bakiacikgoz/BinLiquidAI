"""The core remains usable with no desktop automation package installed."""

from __future__ import annotations

import subprocess
import sys

import pytest

from imperaos.runtime.config import RuntimeConfig


def test_core_cli_does_not_import_or_advertise_desktop_automation() -> None:
    script = """
import importlib.abc
import json
import sys
class RejectDesktopImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(("imperaos.computer_use", "imperaos_computer_use")):
            raise ImportError("Core tried to load optional desktop automation: " + fullname)
sys.meta_path.insert(0, RejectDesktopImports())
from typer.testing import CliRunner
from imperaos.cli import app
runner = CliRunner()
help_result = runner.invoke(app, ["--help"])
assert help_result.exit_code == 0, help_result.output
assert "computer-use" not in help_result.output
result = runner.invoke(app, ["operator", "capabilities", "--json"])
assert result.exit_code == 0, result.exception
payload = json.loads(result.stdout)
desktop_commands = [v for k, v in payload["commands"].items() if k.startswith("computerUse")]
assert desktop_commands and not any(desktop_commands)
for key in ("computerUsePilot", "computerUseVisionRuntime"):
    assert payload["features"][key]["enabled"] is False
    assert payload["features"][key]["reasonCode"] == "COMPUTER_USE_EXTENSION_NOT_INSTALLED"
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "profile", ["default", "balanced", "restricted", "enterprise", "lite", "research"]
)
def test_normal_profiles_disable_computer_use(profile: str) -> None:
    assert RuntimeConfig.from_profile(profile).computer_use.enabled is False


def test_unconfigured_runtime_disables_computer_use() -> None:
    assert RuntimeConfig().computer_use.enabled is False


def test_core_readiness_does_not_depend_on_archived_extension_configuration(monkeypatch) -> None:
    from imperaos.control_plane.readiness import build_readiness_report

    monkeypatch.setattr(
        "imperaos.control_plane.readiness.describe_actor", lambda _: {"verified": False}
    )
    config = RuntimeConfig()
    baseline = build_readiness_report(config)
    config.computer_use.raw_screenshot_persistence = True
    actual = build_readiness_report(config)
    assert actual.status == baseline.status
    assert actual.checks == baseline.checks
    assert actual.blocking_reasons == baseline.blocking_reasons


def test_core_quick_actions_do_not_offer_desktop_execution() -> None:
    from imperaos.control_plane.snapshot import _quick_actions

    actions = _quick_actions(approvals=[], evidence_packs=[])
    assert all("computer-use" not in action.action_id for action in actions)


def test_old_extension_evidence_cannot_reopen_core_desktop_claim(tmp_path) -> None:
    from imperaos.control_plane.claim_guard import ClaimGuard

    config = RuntimeConfig.from_profile("lite")
    config.computer_use.macos_live_enabled = True
    legacy = tmp_path / "computer_use"
    legacy.mkdir()
    (legacy / "macos_qualification_report.json").write_text("{}", encoding="utf-8")
    matrix = ClaimGuard(config=config).evaluate(evidence_root=tmp_path)
    claim = next(item for item in matrix.claims if item.claim_id == "live-macos-computer-use")
    assert claim.status == "blocked"
    assert "COMPUTER_USE_OUTSIDE_CORE_PRODUCT" in claim.blocking_reasons
