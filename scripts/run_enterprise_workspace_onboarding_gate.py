from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SCHEMAS = {
    "enterprise_organization.schema.json",
    "enterprise_workspace.schema.json",
    "enterprise_principal.schema.json",
    "enterprise_membership.schema.json",
    "enterprise_device.schema.json",
    "agent_enrollment_token.schema.json",
    "agent_enrollment_request.schema.json",
    "agent_enrollment_decision.schema.json",
    "enrolled_agent.schema.json",
    "enterprise_workspace_snapshot.schema.json",
    "workspace_permission_decision.schema.json",
}

REQUIRED_FIXTURES = {
    "enterprise_workspace_bootstrap_pass.json",
    "enterprise_workspace_missing_identity_blocked.json",
    "enterprise_workspace_viewer_denied.json",
    "agent_enrollment_token_pass.json",
    "agent_enrollment_expired_token_blocked.json",
    "agent_enrollment_revoked_token_blocked.json",
    "agent_enrollment_raw_token_leak_fail.json",
    "external_agent_not_enrolled_denied.json",
    "external_agent_enrolled_read_only_pass.json",
    "workspace_cross_memory_denied.json",
    "enterprise_workspace_snapshot_ready.json",
}

TARGETED_TESTS = [
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
]


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


def _run(command: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            _resolve(command),
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )
    except FileNotFoundError as exc:
        return {"command": command, "returnCode": 127, "status": "fail", "tail": [str(exc)]}
    return {
        "command": command,
        "returnCode": result.returncode,
        "status": "pass" if result.returncode == 0 else "fail",
        "tail": result.stdout.splitlines()[-25:],
    }


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_static_invariants(root: Path = REPO_ROOT) -> dict[str, Any]:
    schema_dir = root / "contracts" / "control_plane"
    fixture_dir = schema_dir / "fixtures"
    missing_schemas = sorted(REQUIRED_SCHEMAS - {path.name for path in schema_dir.glob("*.json")})
    missing_fixtures = sorted(
        REQUIRED_FIXTURES - {path.name for path in fixture_dir.glob("*.json")}
    )
    blocking_reasons: list[str] = []
    warnings: list[str] = []

    if missing_schemas:
        blocking_reasons.append("missing_contract_schemas")
    if missing_fixtures:
        blocking_reasons.append("missing_contract_fixtures")

    snapshot_path = fixture_dir / "enterprise_workspace_snapshot_ready.json"
    if snapshot_path.exists():
        snapshot = _json(snapshot_path)
        if snapshot.get("rawSecretsExposed") is not False:
            blocking_reasons.append("snapshot_raw_secrets_exposed")
        if snapshot.get("networkListenerEnabled") is not False:
            blocking_reasons.append("network_listener_enabled")
        if snapshot.get("status") != "ready":
            blocking_reasons.append("snapshot_not_ready")
        if not snapshot.get("workspaces"):
            blocking_reasons.append("workspace_missing_from_snapshot")
        if not snapshot.get("memberships"):
            blocking_reasons.append("membership_missing_from_snapshot")
    else:
        blocking_reasons.append("snapshot_fixture_missing")

    token_path = fixture_dir / "agent_enrollment_token_pass.json"
    if token_path.exists():
        token_payload = _json(token_path)
        token_text = json.dumps(token_payload, sort_keys=True)
        if "rawToken" in token_text or "shown-once-token-test-value" in token_text:
            blocking_reasons.append("raw_token_in_pass_fixture")
        if token_payload.get("rawToken") is not None:
            blocking_reasons.append("raw_token_top_level_exposed")
    else:
        blocking_reasons.append("token_pass_fixture_missing")

    leak_fixture_path = fixture_dir / "agent_enrollment_raw_token_leak_fail.json"
    if leak_fixture_path.exists():
        leak_fixture = _json(leak_fixture_path)
        if leak_fixture.get("expectedFailure") != "RAW_TOKEN_FIELD_FORBIDDEN":
            blocking_reasons.append("raw_token_leak_fixture_not_marked_expected_failure")
    else:
        warnings.append("raw_token_leak_negative_fixture_missing")

    docs = {
        "ENTERPRISE_WORKSPACE_ONBOARDING.md",
        "AGENT_ENROLLMENT_RUNBOOK.md",
        "ENTERPRISE_RBAC_CANONICAL_ROLES.md",
        "ENTERPRISE_WORKSPACE_SECURITY_BOUNDARY.md",
    }
    missing_docs = sorted(name for name in docs if not (root / "docs" / name).exists())
    if missing_docs:
        blocking_reasons.append("missing_enterprise_workspace_docs")

    return {
        "status": "pass" if not blocking_reasons else "fail",
        "blockingReasons": blocking_reasons,
        "warnings": warnings,
        "missingSchemas": missing_schemas,
        "missingFixtures": missing_fixtures,
        "missingDocs": missing_docs,
        "checks": {
            "schemasPresent": not missing_schemas,
            "fixturesPresent": not missing_fixtures,
            "snapshotHashOnly": "snapshot_raw_secrets_exposed" not in blocking_reasons,
            "networkListenerDisabled": "network_listener_enabled" not in blocking_reasons,
            "passFixtureHasNoRawToken": "raw_token_in_pass_fixture" not in blocking_reasons,
            "docsPresent": not missing_docs,
        },
    }


def run_gate(
    *,
    profile: str,
    output_root: Path | None = None,
    skip_ui: bool = False,
    skip_commands: bool = False,
) -> dict[str, Any]:
    static_report = evaluate_static_invariants()
    commands: list[dict[str, Any]] = []
    command_plan: list[list[str]] = [
        [sys.executable, "scripts/generate_enterprise_workspace_contract_schemas.py"],
        [sys.executable, "scripts/generate_control_plane_contract_schemas.py"],
        [sys.executable, "-m", "pytest", "-q", *TARGETED_TESTS],
        ["git", "diff", "--check"],
    ]
    if not skip_ui:
        command_plan.extend(
            [
                [
                    "corepack",
                    "pnpm",
                    "--dir",
                    "apps/operator-panel",
                    "exec",
                    "vitest",
                    "run",
                    "src/enterprise-workspace/EnterpriseWorkspaceView.test.tsx",
                    "src/enterprise-workspace/AgentEnrollmentView.test.tsx",
                    "src/routeRegistry.test.ts",
                ],
                ["corepack", "pnpm", "--dir", "apps/operator-panel", "lint"],
                ["corepack", "pnpm", "--dir", "apps/operator-panel", "build"],
                [
                    "corepack",
                    "pnpm",
                    "--dir",
                    "apps/operator-panel",
                    "exec",
                    "playwright",
                    "test",
                    "e2e/enterprise-workspace.spec.ts",
                    "--pass-with-no-tests",
                ],
            ]
        )

    if not skip_commands and static_report["status"] == "pass":
        for command in command_plan:
            result = _run(command)
            commands.append(result)
            if result["returnCode"] != 0:
                break

    commands_pass = all(result["returnCode"] == 0 for result in commands)
    status = "pass" if static_report["status"] == "pass" and commands_pass else "fail"
    report = {
        "schemaVersion": "enterprise-workspace.onboarding-gate/v1",
        "generatedAtUtc": _now(),
        "profile": profile,
        "status": status,
        "static": static_report,
        "commands": commands,
        "skipUi": skip_ui,
        "skipCommands": skip_commands,
        "makeRequired": False,
    }
    if output_root is not None:
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "enterprise-workspace-onboarding-gate.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_root / "ENTERPRISE_WORKSPACE_ONBOARDING_GATE.md").write_text(
            render_markdown(report),
            encoding="utf-8",
        )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    static = report["static"]
    lines = [
        "# Enterprise Workspace Onboarding Gate",
        "",
        f"- Status: `{report['status']}`",
        f"- Profile: `{report['profile']}`",
        f"- Generated: `{report['generatedAtUtc']}`",
        f"- Static blockers: `{', '.join(static['blockingReasons']) or 'none'}`",
        f"- Commands run: `{len(report['commands'])}`",
        "",
        "## Checks",
    ]
    for name, passed in static["checks"].items():
        lines.append(f"- `{name}`: `{'pass' if passed else 'fail'}`")
    lines.append("")
    lines.append("## Command Results")
    if not report["commands"]:
        lines.append("- No commands were executed.")
    for result in report["commands"]:
        command = " ".join(result["command"])
        lines.append(f"- `{result['status']}` `{command}`")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the enterprise workspace onboarding gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/enterprise-workspace-onboarding"),
    )
    parser.add_argument("--skip-ui", action="store_true")
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    report = run_gate(
        profile=args.profile,
        output_root=args.output_root,
        skip_ui=args.skip_ui,
        skip_commands=args.skip_commands,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']} profile={report['profile']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
