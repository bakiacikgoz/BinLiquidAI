from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_provider_governance_pr_readiness_reports_required_gates(tmp_path: Path) -> None:
    output = tmp_path / "readiness.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/check_provider_governance_pr_readiness.py",
            "--profile",
            "enterprise",
            "--branch",
            "codex/provider-governance-v1",
            "--output",
            str(output),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    assert payload["branch"] == "codex/provider-governance-v1"
    assert payload["requiredGates"]["provider_native_gate"] == "pass"
    assert payload["requiredGates"]["design_partner_rc_audit_gate"] == "pass"
    assert payload["blockers"] == []
