from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "assistant-system-knowledge"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _resolve(command: list[str]) -> list[str]:
    executable = command[0]
    candidates = [executable]
    if os.name == "nt" and Path(executable).suffix == "":
        candidates = [f"{executable}.cmd", f"{executable}.exe", executable]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved, *command[1:]]
    return command


def _vitest_command() -> list[str]:
    suffix = ".cmd" if os.name == "nt" else ""
    local = REPO_ROOT / "apps" / "operator-panel" / "node_modules" / ".bin" / f"vitest{suffix}"
    if local.exists():
        return [
            str(local),
            "run",
            "src/assistant",
            "src/components/assistant",
            "src/bridge.test.ts",
        ]
    return [
        "corepack",
        "pnpm",
        "--dir",
        "apps/operator-panel",
        "exec",
        "vitest",
        "run",
        "src/assistant",
        "src/components/assistant",
        "src/bridge.test.ts",
    ]


def _run(
    command: list[str],
    *,
    name: str,
    required: bool = True,
    cwd: Path = REPO_ROOT,
) -> dict[str, Any]:
    started = time.monotonic()
    env = {**os.environ, "COREPACK_ENABLE_AUTO_PIN": "0"}
    try:
        result = subprocess.run(
            _resolve(command),
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
    except FileNotFoundError as exc:
        return {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 127,
            "status": "fail",
            "reasonCode": "EXECUTABLE_MISSING",
            "durationMs": int((time.monotonic() - started) * 1000),
            "tail": [str(exc)],
        }
    return {
        "name": name,
        "command": command,
        "required": required,
        "returnCode": result.returncode,
        "status": "pass" if result.returncode == 0 else "fail",
        "reasonCode": "OK" if result.returncode == 0 else "COMMAND_FAILED",
        "durationMs": int((time.monotonic() - started) * 1000),
        "tail": result.stdout.splitlines()[-30:],
    }


def build_command_plan(profile: str, output_root: Path) -> list[dict[str, Any]]:
    return [
        {
            "name": "schema_generation",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/generate_assistant_knowledge_contract_schemas.py",
            ],
            "required": True,
        },
        {
            "name": "python_knowledge_tests",
            "command": [
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "-m",
                "pytest",
                "-q",
                "tests/test_assistant_system_knowledge.py",
                "tests/test_assistant_system_knowledge_regression.py",
                "tests/test_assistant_cli.py",
            ],
            "required": True,
        },
        {
            "name": "knowledge_build",
            "command": [
                "uv",
                "run",
                "binliquid",
                "assistant",
                "knowledge",
                "build",
                "--profile",
                profile,
                "--output-root",
                str(output_root),
                "--json",
            ],
            "required": True,
        },
        {
            "name": "knowledge_search_regression",
            "command": [
                "uv",
                "run",
                "binliquid",
                "assistant",
                "knowledge",
                "search",
                "--profile",
                profile,
                "--index-root",
                str(output_root),
                "--query",
                "AgeisOs sisteminde nasıl bir agent'e görev verebilirim?",
                "--include-context",
                "--json",
            ],
            "required": True,
        },
        {
            "name": "frontend_knowledge_tests",
            "command": _vitest_command(),
            "required": True,
            "cwd": REPO_ROOT / "apps" / "operator-panel",
        },
        {
            "name": "rust_bridge_assistant_tests",
            "command": [
                "cargo",
                "test",
                "-q",
                "--manifest-path",
                "apps/operator-panel/src-tauri/Cargo.toml",
                "--target-dir",
                "apps/operator-panel/src-tauri/target-codex-test",
                "assistant",
            ],
            "required": True,
        },
        {
            "name": "staged_whitespace",
            "command": ["git", "diff", "--check"],
            "required": True,
        },
    ]


def run_assistant_system_knowledge_gate(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    profile: str = "enterprise",
    skip_commands: bool = False,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    if not skip_commands:
        for item in build_command_plan(profile, output_root):
            result = _run(
                item["command"],
                name=item["name"],
                required=item["required"],
                cwd=item.get("cwd", REPO_ROOT),
            )
            checks.append(result)
            if result["required"] and result["status"] == "fail":
                break
    blockers = [
        f"ASSISTANT_SYSTEM_KNOWLEDGE_GATE_CHECK_FAILED:{check['name']}"
        for check in checks
        if check["required"] and check["status"] == "fail"
    ]
    status = "pass" if not blockers else "fail"
    report = {
        "schemaVersion": "assistant.system-knowledge-gate/v1",
        "generatedAtUtc": _now(),
        "profile": profile,
        "status": status,
        "checks": checks,
        "noShipBlockers": blockers,
        "blockingReasons": blockers,
        "artifacts": [
            str(output_root / "assistant_system_knowledge_gate.json"),
            str(output_root / "SYSTEM_KNOWLEDGE_GATE.md"),
        ],
    }
    (output_root / "assistant_system_knowledge_gate.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "SYSTEM_KNOWLEDGE_GATE.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Assistant System Knowledge Gate",
        "",
        f"- Status: `{report['status']}`",
        f"- Profile: `{report['profile']}`",
        "",
        "## Checks",
    ]
    for check in report["checks"]:
        lines.append(f"- `{check['status']}` `{check['name']}` `{check['reasonCode']}`")
    if report["noShipBlockers"]:
        lines.extend(["", "## No-Ship Blockers"])
        lines.extend(f"- `{item}`" for item in report["noShipBlockers"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run assistant system knowledge gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = run_assistant_system_knowledge_gate(
        output_root=args.output_root,
        profile=args.profile,
        skip_commands=args.skip_commands,
    )
    if args.json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']} output={args.output_root}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
