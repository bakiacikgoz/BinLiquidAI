from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.run_enterprise_workspace_onboarding_gate import (
    evaluate_static_invariants,
    render_markdown,
    run_gate,
)


def test_enterprise_workspace_onboarding_gate_static_invariants_pass() -> None:
    report = evaluate_static_invariants()

    assert report["status"] == "pass"
    assert report["checks"]["schemasPresent"] is True
    assert report["checks"]["fixturesPresent"] is True
    assert report["checks"]["snapshotHashOnly"] is True
    assert report["checks"]["networkListenerDisabled"] is True
    assert report["checks"]["passFixtureHasNoRawToken"] is True


def test_onboarding_gate_writes_report_without_commands(tmp_path: Path) -> None:
    report = run_gate(
        profile="enterprise",
        output_root=tmp_path,
        skip_ui=True,
        skip_commands=True,
    )
    markdown = render_markdown(report)

    assert report["status"] == "pass"
    assert report["skipCommands"] is True
    assert "Enterprise Workspace Onboarding Gate" in markdown
    assert (tmp_path / "enterprise-workspace-onboarding-gate.json").exists()
    assert (tmp_path / "ENTERPRISE_WORKSPACE_ONBOARDING_GATE.md").exists()


def test_enterprise_workspace_onboarding_gate_cli_outputs_json_without_raw_token() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_enterprise_workspace_onboarding_gate.py",
            "--profile",
            "enterprise",
            "--skip-ui",
            "--skip-commands",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schemaVersion"] == "enterprise-workspace.onboarding-gate/v1"
    assert payload["status"] == "pass"
    assert "shown-once-token-test-value" not in result.stdout
