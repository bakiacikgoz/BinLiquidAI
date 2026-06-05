from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_design_partner_rc_pack_generator(tmp_path: Path) -> None:
    output = tmp_path / "design-partner-rc"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/generate_design_partner_rc_pack.py",
            "--profile",
            "lite",
            "--output",
            str(output),
            "--state-root",
            str(tmp_path / "cp"),
            "--evidence-root",
            str(tmp_path / "artifacts"),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["version"] == "control-plane.design-partner-rc-pack/v1"
    assert payload["status"] == "conditional"
    assert payload["claimBoundaries"]["computerUseLive"] == "blocked"
    assert payload["artifacts"]
    assert all("status" in item for item in payload["artifacts"])
    assert (output / "manifest.json").exists()
    assert (output / "DESIGN_PARTNER_RC_REPORT.md").exists()


def test_design_partner_rc_pack_fail_on_conditional(tmp_path: Path) -> None:
    output = tmp_path / "design-partner-rc"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/generate_design_partner_rc_pack.py",
            "--profile",
            "lite",
            "--output",
            str(output),
            "--state-root",
            str(tmp_path / "cp"),
            "--evidence-root",
            str(tmp_path / "artifacts"),
            "--fail-on-conditional",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["status"] == "conditional"
