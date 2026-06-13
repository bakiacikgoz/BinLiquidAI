from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_run_pr_readiness_gate_wraps_provider_governance_checker(tmp_path: Path) -> None:
    output = tmp_path / "readiness.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_pr_readiness_gate.py",
            "--profile",
            "enterprise",
            "--branch",
            "main",
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
    assert payload["branch"] == "main"
    assert payload["requiredGates"]["provider_native_gate"] == "pass"
