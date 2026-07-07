from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "enterprise-workspace-release-closure"

TARGETED_PYTESTS = [
    "tests/test_enterprise_workspace_models.py",
    "tests/test_enterprise_workspace_rbac.py",
    "tests/test_agent_enrollment.py",
    "tests/test_enterprise_workspace_contracts.py",
    "tests/test_enterprise_workspace_store.py",
    "tests/test_enterprise_workspace_cli.py",
    "tests/test_agent_enrollment_cli.py",
    "tests/test_agent_enrollment_evidence.py",
    "tests/test_agent_registry_workspace_binding.py",
    "tests/test_external_gateway_enrollment_guard.py",
    "tests/test_memory_enterprise_workspace_binding.py",
    "tests/test_control_plane_snapshot_enterprise_workspace.py",
    "tests/test_enterprise_workspace_onboarding_gate.py",
    "tests/test_control_plane_external_agent_client.py",
    "tests/test_design_partner_rc_audit_gate.py",
    "tests/test_mainline_rc_freeze_cli.py",
    "tests/test_pr_readiness_gate.py",
    "tests/test_provider_governance_pr_readiness.py",
]

RAW_MARKERS = (
    "rawToken",
    "shown-once-token-test-value",
    "sk-",
    "BEGIN PRIVATE KEY",
    "password=",
    "secret=",
    "Authorization: Bearer",
)

RAW_SCAN_PATHS = (
    "contracts/control_plane",
    "docs/AGENT_ENROLLMENT_RUNBOOK.md",
    "docs/ENTERPRISE_RBAC_CANONICAL_ROLES.md",
    "docs/ENTERPRISE_WORKSPACE_ONBOARDING.md",
    "docs/ENTERPRISE_WORKSPACE_SECURITY_BOUNDARY.md",
    "docs/ENTERPRISE_WORKSPACE_RELEASE_CLOSURE.md",
    "docs/WINDOWS_GATE_TROUBLESHOOTING.md",
    "artifacts/enterprise-workspace-release-closure",
)

RAW_SCAN_ALLOWLIST = (
    "contracts/control_plane/fixtures/agent_enrollment_raw_token_leak_fail.json",
)


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


def _command_cwd(command: list[str]) -> Path:
    if command:
        local_bin = REPO_ROOT / "apps" / "operator-panel" / "node_modules" / ".bin"
        try:
            if Path(command[0]).resolve().parent == local_bin.resolve():
                return REPO_ROOT / "apps" / "operator-panel"
        except OSError:
            pass
    return REPO_ROOT


def _run(command: list[str], *, name: str, required: bool = True) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            _resolve(command),
            cwd=_command_cwd(command),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
    except FileNotFoundError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 127,
            "status": "blocked_environment",
            "durationMs": duration_ms,
            "reasonCode": "EXECUTABLE_MISSING",
            "tail": [_redact(str(exc))],
        }
    duration_ms = int((time.monotonic() - started) * 1000)
    status = "pass" if result.returncode == 0 else "fail"
    reason = "OK" if result.returncode == 0 else "COMMAND_FAILED"
    return {
        "name": name,
        "command": command,
        "required": required,
        "returnCode": result.returncode,
        "status": status,
        "durationMs": duration_ms,
        "reasonCode": reason,
        "tail": [_redact(line) for line in result.stdout.splitlines()[-30:]],
    }


def _node_bin(name: str) -> str | None:
    suffix = ".cmd" if os.name == "nt" else ""
    candidate = REPO_ROOT / "apps" / "operator-panel" / "node_modules" / ".bin" / f"{name}{suffix}"
    return str(candidate) if candidate.exists() else None


def _operator_panel_exec(name: str, args: list[str]) -> list[str]:
    local = _node_bin(name)
    if local is not None:
        return [local, *args]
    return ["corepack", "pnpm", "--dir", "apps/operator-panel", "exec", name, *args]


def _operator_panel_script(script: str) -> list[str]:
    if script == "test":
        return _operator_panel_exec("vitest", ["run"])
    if script == "lint":
        local = _node_bin("eslint")
        if local is not None:
            return [local, "."]
    return ["corepack", "pnpm", "--dir", "apps/operator-panel", script]


def _redact(value: str) -> str:
    return value.replace(str(REPO_ROOT), "<repo>").replace(str(Path.home()), "<home>")


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _pytest_command(mode: Literal["full", "targeted", "skip"]) -> list[str] | None:
    if mode == "skip":
        return None
    if mode == "targeted":
        return [sys.executable, "-m", "pytest", "-q", *TARGETED_PYTESTS]
    return [sys.executable, "-m", "pytest", "-q", "--maxfail=20", "--tb=short"]


def parse_pytest_failures(lines: list[str]) -> list[str]:
    failures: list[str] = []
    pattern = re.compile(r"FAILED\s+([^\s]+)")
    for line in lines:
        match = pattern.search(line)
        if match:
            failures.append(match.group(1))
    return failures


def scan_raw_markers(output_root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for relative_path in RAW_SCAN_PATHS:
        root = REPO_ROOT / relative_path
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else list(root.rglob("*"))
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative in RAW_SCAN_ALLOWLIST:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for marker in RAW_MARKERS:
                if marker in text:
                    findings.append({"path": relative, "marker": marker})
    return {
        "status": "pass" if not findings else "fail",
        "findings": findings,
        "scannedRoots": list(RAW_SCAN_PATHS),
        "outputRoot": output_root.relative_to(REPO_ROOT).as_posix()
        if output_root.is_relative_to(REPO_ROOT)
        else str(output_root),
    }


def build_command_plan(
    profile: str,
    pytest_mode: Literal["full", "targeted", "skip"],
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = [
        {
            "name": "ruff",
            "command": ["uv", "run", "--extra", "dev", "ruff", "check", "."],
            "required": True,
        },
        {
            "name": "generate_enterprise_workspace_schemas",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/generate_enterprise_workspace_contract_schemas.py",
            ],
            "required": True,
        },
        {
            "name": "generate_control_plane_schemas",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/generate_control_plane_contract_schemas.py",
            ],
            "required": True,
        },
        {
            "name": "enterprise_workspace_onboarding_gate",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_enterprise_workspace_onboarding_gate.py",
                "--profile",
                profile,
                "--json",
            ],
            "required": True,
        },
    ]
    pytest = _pytest_command(pytest_mode)
    if pytest is not None:
        commands.append({"name": f"pytest_{pytest_mode}", "command": pytest, "required": True})
    commands.extend(
        [
            {
                "name": "operator_panel_test",
                "command": _operator_panel_script("test"),
                "required": True,
            },
            {
                "name": "operator_panel_lint",
                "command": _operator_panel_script("lint"),
                "required": True,
            },
            {
                "name": "operator_panel_typecheck",
                "command": _operator_panel_exec("tsc", ["-b"]),
                "required": True,
            },
            {
                "name": "operator_panel_build",
                "command": _operator_panel_exec("vite", ["build"]),
                "required": True,
            },
            {
                "name": "enterprise_workspace_e2e",
                "command": _operator_panel_exec(
                    "playwright",
                    ["test", "e2e/enterprise-workspace.spec.ts", "--pass-with-no-tests"],
                ),
                "required": True,
            },
            {
                "name": "tauri_cargo_test_stable_target",
                "command": [
                    "cargo",
                    "test",
                    "-q",
                    "--manifest-path",
                    "apps/operator-panel/src-tauri/Cargo.toml",
                    "--target-dir",
                    "apps/operator-panel/src-tauri/target-codex-test",
                ],
                "required": True,
            },
            {
                "name": "tauri_cargo_test_default_target_diagnostic",
                "command": [
                    "cargo",
                    "test",
                    "-q",
                    "--manifest-path",
                    "apps/operator-panel/src-tauri/Cargo.toml",
                ],
                "required": False,
            },
            {"name": "git_diff_check", "command": ["git", "diff", "--check"], "required": True},
        ]
    )
    return commands


def run_closure_gate(
    *,
    profile: str,
    output_root: Path,
    pytest_mode: Literal["full", "targeted", "skip"],
    skip_commands: bool = False,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    for name in ("closure_report.json", "closure_report.md", "pr_body.md"):
        (output_root / name).unlink(missing_ok=True)
    commands: list[dict[str, Any]] = []
    if not skip_commands:
        for item in build_command_plan(profile, pytest_mode):
            result = _run(item["command"], name=item["name"], required=item["required"])
            if result["name"].startswith("pytest"):
                result["pytestFailures"] = parse_pytest_failures(result["tail"])
            commands.append(result)
            if item["required"] and result["returnCode"] != 0:
                break

    raw_scan = scan_raw_markers(output_root)
    required_failures = [
        result
        for result in commands
        if result["required"] and result["returnCode"] != 0
    ]
    blocked_environment = [
        result for result in commands if result["status"] == "blocked_environment"
    ]
    tauri_diagnostic = next(
        (
            result
            for result in commands
            if result["name"] == "tauri_cargo_test_default_target_diagnostic"
        ),
        None,
    )
    blocking_reasons = [f"command_failed:{result['name']}" for result in required_failures]
    if raw_scan["status"] != "pass":
        blocking_reasons.append("raw_marker_scan_failed")
    status = "pass" if not blocking_reasons else "fail"
    report = {
        "schemaVersion": "enterprise-workspace.release-closure/v1",
        "generatedAtUtc": _now(),
        "profile": profile,
        "status": status,
        "branch": _git(["branch", "--show-current"]),
        "headSha": _git(["rev-parse", "HEAD"]),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "pythonExecutable": sys.executable,
        "pytestMode": pytest_mode,
        "commandResults": commands,
        "blockingReasons": blocking_reasons,
        "blockedEnvironment": blocked_environment,
        "tauri": {
            "status": "pass"
            if not any(
                result["name"] == "tauri_cargo_test_stable_target"
                for result in required_failures
            )
            else "fail",
            "defaultTargetDiagnostic": tauri_diagnostic,
        },
        "rawLeakScan": raw_scan,
        "gitStatusShort": _git(["status", "--short"]),
        "artifacts": [
            "artifacts/enterprise-workspace-release-closure/closure_report.json",
            "artifacts/enterprise-workspace-release-closure/closure_report.md",
            "artifacts/enterprise-workspace-release-closure/pr_body.md",
        ],
        "pushPerformed": False,
    }
    _write_outputs(output_root, report)
    return report


def _write_outputs(output_root: Path, report: dict[str, Any]) -> None:
    (output_root / "closure_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "closure_report.md").write_text(render_markdown(report), encoding="utf-8")
    (output_root / "pr_body.md").write_text(render_pr_body(report), encoding="utf-8")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Enterprise Workspace Release Closure",
        "",
        f"- Status: `{report['status']}`",
        f"- Branch: `{report['branch']}`",
        f"- Head: `{report['headSha']}`",
        f"- Pytest mode: `{report['pytestMode']}`",
        f"- Tauri: `{report['tauri']['status']}`",
        f"- Raw leak scan: `{report['rawLeakScan']['status']}`",
        f"- Git status: `{'clean' if not report['gitStatusShort'] else 'dirty'}`",
        "",
        "## Commands",
    ]
    for result in report["commandResults"]:
        command = " ".join(_redact(str(part)) for part in result["command"])
        lines.append(f"- `{result['status']}` `{result['name']}` `{command}`")
    if report["blockingReasons"]:
        lines.extend(["", "## Blocking Reasons"])
        lines.extend(f"- `{reason}`" for reason in report["blockingReasons"])
    if report["tauri"].get("defaultTargetDiagnostic"):
        diagnostic = report["tauri"]["defaultTargetDiagnostic"]
        lines.extend(
            [
                "",
                "## Tauri Diagnostic",
                (
                    f"- Default target command: `{diagnostic['status']}` "
                    f"`{diagnostic['reasonCode']}`"
                ),
                "- Stable target-dir command is the release validation path.",
            ]
        )
    return "\n".join(lines) + "\n"


def render_pr_body(report: dict[str, Any]) -> str:
    validation = [
        f"- Closure gate: `{report['status']}`",
        f"- Pytest mode: `{report['pytestMode']}`",
        f"- Tauri: `{report['tauri']['status']}`",
        f"- Raw token/secret persistence: `{report['rawLeakScan']['status']}`",
        f"- Git status: `{'clean' if not report['gitStatusShort'] else 'dirty'}`",
    ]
    return (
        "## Summary\n"
        "- Enterprise Workspace Onboarding & Agent Enrollment v1\n"
        "- Release closure and cross-platform gate reconciliation\n\n"
        "## Validation\n"
        + "\n".join(validation)
        + "\n\n"
        "## Security/Privacy\n"
        "- Raw enrollment tokens remain shown-once only and are not persisted.\n"
        "- Network listener remains disabled by default.\n"
        "- Release closure includes raw marker scanning.\n\n"
        "## Known Environment Notes\n"
        "- Windows without `make` can run the Python closure gate directly.\n"
        "- Tauri validation uses an explicit target-dir to avoid OneDrive path misresolution.\n\n"
        "## Rollback\n"
        "- Revert the enterprise workspace branch commits; no runtime migration is required.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run enterprise workspace release closure gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--pytest-mode", choices=["full", "targeted", "skip"], default="full")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    report = run_closure_gate(
        profile=args.profile,
        output_root=args.output_root,
        pytest_mode=args.pytest_mode,
        skip_commands=args.skip_commands,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']} output={args.output_root}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
