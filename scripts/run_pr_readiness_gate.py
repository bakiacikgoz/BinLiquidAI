from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PR readiness gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--branch", default="")
    parser.add_argument("--output", default="artifacts/provider-governance-pr/readiness.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "scripts/check_provider_governance_pr_readiness.py",
        "--profile",
        args.profile,
        "--branch",
        args.branch,
        "--output",
        args.output,
    ]
    if args.json:
        cmd.append("--json")
    raise SystemExit(subprocess.run(cmd, cwd=REPO_ROOT, check=False).returncode)


if __name__ == "__main__":
    main()
