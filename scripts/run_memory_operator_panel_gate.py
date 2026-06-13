from __future__ import annotations

import json
import subprocess
from pathlib import Path


def main() -> None:
    commands = [
        ["corepack", "pnpm", "--dir", "apps/operator-panel", "test", "--", "memory"],
        [
            "corepack",
            "pnpm",
            "--dir",
            "apps/operator-panel",
            "test:e2e",
            "--",
            "memory-governance.spec.ts",
        ],
    ]
    results = []
    for command in commands:
        completed = subprocess.run(command, check=False)
        results.append({"command": command, "exitCode": completed.returncode})
    status = "pass" if all(item["exitCode"] == 0 for item in results) else "fail"
    payload = {"status": status, "results": results}
    out = Path("artifacts/memory-governance/memory_operator_panel_gate.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
