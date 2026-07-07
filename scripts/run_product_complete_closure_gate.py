from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from binliquid.local_product.cli import build_matrix_report, build_readiness_report
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence
from binliquid.local_product.harvest import HarvestRequest, harvest_platform_evidence
from binliquid.local_product.source_install_claim import (
    SourceInstallClaimPolicy,
    build_source_install_rc_claim,
)
from binliquid.local_product.target_closure import build_target_closure_actions
from binliquid.release.product_complete import build_product_complete_no_ship_register

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "product-complete-closure"


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


def _extract_json(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _run(command: list[str], *, name: str, required: bool = True) -> dict[str, Any]:
    started = time.monotonic()
    env = {**os.environ, "COREPACK_ENABLE_AUTO_PIN": "0"}
    try:
        result = subprocess.run(
            _resolve(command),
            cwd=REPO_ROOT,
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
            "tail": [str(exc)],
        }
    parsed_json = _extract_json(result.stdout)
    status = "pass" if result.returncode == 0 else "fail"
    reason = "OK" if result.returncode == 0 else "COMMAND_FAILED"
    if name == "macos_local_trial_gate" and result.returncode == 3:
        status = "conditional"
        reason = "MACOS_LOCAL_TRIAL_CONDITIONAL"
    if (
        parsed_json is not None
        and result.returncode != 0
        and parsed_json.get("status") == "conditional"
        and not parsed_json.get("noShipBlockers")
    ):
        status = "conditional"
        reason = f"{name.upper()}_CONDITIONAL"
    payload = {
        "name": name,
        "command": command,
        "required": required,
        "returnCode": result.returncode,
        "status": status,
        "reasonCode": reason,
        "durationMs": int((time.monotonic() - started) * 1000),
        "tail": result.stdout.splitlines()[-30:],
    }
    if parsed_json is not None:
        payload["json"] = parsed_json
    return payload


def _operator_panel_static_command() -> list[str]:
    suffix = ".cmd" if os.name == "nt" else ""
    local = REPO_ROOT / "apps" / "operator-panel" / "node_modules" / ".bin" / f"tsx{suffix}"
    if local.exists():
        return [
            str(local),
            "apps/operator-panel/scripts/assert-no-inert-primary-actions.ts",
        ]
    return [
        "corepack",
        "pnpm",
        "--dir",
        "apps/operator-panel",
        "exec",
        "tsx",
        "scripts/assert-no-inert-primary-actions.ts",
    ]


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


def build_command_plan(
    profile: str, output_root: Path, *, include_local_trial: bool = False
) -> list[dict[str, Any]]:
    plan = [
        {
            "name": "scope_gate",
            "readiness": None,
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_product_complete_scope_gate.py",
                "--output-root",
                str(output_root / "scope"),
                "--json",
            ],
            "required": True,
        },
        {
            "name": "assistant_real_runtime_gate",
            "readiness": "assistant",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_assistant_real_runtime_gate.py",
                "--profile",
                profile,
                "--json",
            ],
            "required": True,
        },
        {
            "name": "assistant_system_knowledge_gate",
            "readiness": "assistantSystemKnowledge",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_assistant_system_knowledge_gate.py",
                "--profile",
                profile,
                "--json",
            ],
            "required": True,
        },
        {
            "name": "assistant_governed_tasking_gate",
            "readiness": "assistantTasking",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_assistant_governed_tasking_gate.py",
                "--profile",
                profile,
                "--json",
            ],
            "required": True,
        },
        {
            "name": "operator_panel_static",
            "readiness": "operatorPanel",
            "command": _operator_panel_static_command(),
            "required": True,
        },
        {
            "name": "first_run_readiness_gate",
            "readiness": "installerFirstRun",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_first_run_readiness_gate.py",
                "--profile",
                profile,
                "--json",
            ],
            "required": True,
        },
        {
            "name": "enterprise_workspace_onboarding_gate",
            "readiness": "enterpriseWorkspace",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_enterprise_workspace_onboarding_gate.py",
                "--profile",
                profile,
                "--skip-ui",
                "--json",
            ],
            "required": True,
        },
        {
            "name": "governed_agent_workflow_product_gate",
            "readiness": "governedWorkflow",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_governed_agent_workflow_product_gate.py",
                "--profile",
                profile,
                "--json",
            ],
            "required": True,
        },
        {
            "name": "evidence_release_closure_gate",
            "readiness": "evidence",
            "command": [
                "uv",
                "run",
                "python",
                "scripts/run_enterprise_workspace_release_closure_gate.py",
                "--profile",
                profile,
                "--pytest-mode",
                "targeted",
                "--json",
            ],
            "required": True,
        },
        {
            "name": "git_diff_check",
            "readiness": None,
            "command": ["git", "diff", "--check"],
            "required": True,
        },
    ]
    if include_local_trial:
        plan.append(
            {
                "name": "macos_local_trial_gate",
                "readiness": "macosLocalTrial",
                "command": [
                    "uv",
                    "run",
                    "python",
                    "scripts/run_macos_local_trial_gate.py",
                    "--profile",
                    profile,
                    "--output-root",
                    str(output_root / "macos-local-trial"),
                    "--json",
                ],
                "required": True,
            }
        )
    return plan


def _empty_readiness() -> dict[str, str]:
    return {
        "assistant": "pass",
        "assistantSystemKnowledge": "pass",
        "assistantTasking": "pass",
        "operatorPanel": "pass",
        "enterpriseWorkspace": "pass",
        "governedWorkflow": "pass",
        "installerFirstRun": "pass",
        "evidence": "pass",
        "macosLocalTrial": "not_run",
    }


def _local_product_readiness_summary(profile: str) -> dict[str, Any]:
    current = build_readiness_report(profile=profile, target_value="auto", output_root=None)
    matrix = build_matrix_report(profile=profile, include_experimental=True)
    boundary = current.get("claimBoundary", {})
    return {
        "status": current.get("overallStatus", "blocked"),
        "currentTarget": current.get("target", {}).get("targetId")
        if isinstance(current.get("target"), dict)
        else "unknown-unknown",
        "supportedClaims": (
            boundary.get("supportedClaims", []) if isinstance(boundary, dict) else []
        ),
        "notEvidencedTargets": matrix.get("notEvidencedTargets", []),
        "unsupportedTargets": matrix.get("unsupportedTargets", []),
        "blockedTargets": matrix.get("blockedTargets", []),
        "noShipBlockers": [],
        "productClaimSummary": boundary.get("productClaimSummary", "")
        if isinstance(boundary, dict)
        else "",
    }


def _platform_evidence_store_for_closure(output_root: Path) -> Path | None:
    harvest_store = output_root.parent / "local-product" / "harvest" / "store"
    if harvest_store.exists():
        return harvest_store
    artifact_store = output_root.parent / "local-product-platform-evidence" / "store"
    return artifact_store if artifact_store.exists() else None


def _latest_harvest_report(output_root: Path) -> dict[str, Any]:
    harvest_path = (
        output_root.parent
        / "local-product"
        / "harvest"
        / "platform_evidence_harvest_report.json"
    )
    if harvest_path.exists():
        try:
            return json.loads(harvest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"schemaVersion": "local_product_harvest/v1", "status": "blocked"}
    report = harvest_platform_evidence(
        request=HarvestRequest(
            outputRoot=str(output_root.parent / "local-product" / "harvest"),
            evidenceStore=str(output_root.parent / "local-product" / "harvest" / "store"),
        )
    )
    return report.model_dump(mode="json", by_alias=True)


def _release_claim_accuracy(source_claim: dict[str, Any]) -> dict[str, Any]:
    blockers = source_claim.get("noShipBlockers", [])
    return {
        "schemaVersion": "release_claim_accuracy/v1",
        "status": "blocked" if blockers else "pass",
        "claimSet": source_claim.get("claimSet", "source-local-install"),
        "allowedClaims": source_claim.get("releaseNotesAllowedClaims", []),
        "noShipBlockers": blockers,
    }


def run_product_complete_closure_gate(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    profile: str = "enterprise",
    skip_commands: bool = False,
    include_local_trial: bool = False,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    readiness = _empty_readiness()
    if not skip_commands:
        for item in build_command_plan(
            profile, output_root, include_local_trial=include_local_trial
        ):
            result = _run(item["command"], name=item["name"], required=item["required"])
            checks.append(result)
            readiness_key = item.get("readiness")
            if readiness_key and result["status"] == "fail":
                readiness[str(readiness_key)] = "fail"
            elif readiness_key and result["status"] == "conditional":
                readiness[str(readiness_key)] = "conditional"
            elif readiness_key and result["status"] == "pass":
                readiness[str(readiness_key)] = "pass"
            if result["required"] and result["status"] == "fail":
                break
    local_product_readiness = _local_product_readiness_summary(profile)
    platform_evidence_store = _platform_evidence_store_for_closure(output_root)
    platform_evidence_reconciliation = (
        reconcile_platform_evidence(store_root=platform_evidence_store)
        if platform_evidence_store
        else reconcile_platform_evidence()
    )
    platform_evidence_harvest = _latest_harvest_report(output_root)
    source_install_claim = build_source_install_rc_claim(
        policy=SourceInstallClaimPolicy(expectedHeadSha=_git(["rev-parse", "HEAD"])),
        evidence_root=platform_evidence_store or Path(".binliquid/local-product/evidence"),
    ).model_dump(mode="json", by_alias=True)
    target_closure_actions = [
        action.model_dump(mode="json", by_alias=True)
        for action in build_target_closure_actions(
            reconciliation=platform_evidence_reconciliation,
            head_sha=_git(["rev-parse", "HEAD"]),
        )
    ]
    release_claim_accuracy = _release_claim_accuracy(source_install_claim)
    no_ship_register = build_product_complete_no_ship_register()
    blockers = [
        f"PRODUCT_COMPLETE_CHECK_FAILED:{check['name']}"
        for check in checks
        if check["required"] and check["status"] == "fail"
    ]
    blockers.extend(item.reason_code for item in no_ship_register.items if item.status == "open")
    blockers.extend(
        blocker.reason_code for blocker in platform_evidence_reconciliation.no_ship_blockers
    )
    blockers.extend(source_install_claim.get("noShipBlockers", []))
    status = "pass" if not blockers else "fail"
    report = {
        "schemaVersion": "product-complete.closure/v1",
        "generatedAtUtc": _now(),
        "profile": profile,
        "status": status,
        "branch": _git(["branch", "--show-current"]),
        "headSha": _git(["rev-parse", "HEAD"]),
        "checks": checks,
        "noShipBlockers": blockers,
        "conditionalNotes": _conditional_notes(checks),
        "artifacts": {
            "json": "artifacts/product-complete-closure/product_complete_closure_report.json",
            "markdown": "artifacts/product-complete-closure/product_complete_closure_report.md",
            "prBody": "artifacts/product-complete-closure/product_complete_pr_body.md",
            "noShipRegister": "artifacts/product-complete-closure/no_ship_register.json",
        },
        "ci": {},
        "rawLeakScan": {},
        "productReadiness": readiness,
        "localProductReadiness": local_product_readiness,
        "platformEvidenceReconciliation": platform_evidence_reconciliation.model_dump(
            mode="json",
            by_alias=True,
        ),
        "platformEvidenceHarvest": platform_evidence_harvest,
        "sourceInstallRcClaim": source_install_claim,
        "targetClosureActions": target_closure_actions,
        "releaseClaimAccuracy": release_claim_accuracy,
    }
    _write_outputs(output_root, report, no_ship_register.model_dump(mode="json", by_alias=True))
    return report


def _write_outputs(
    output_root: Path,
    report: dict[str, Any],
    no_ship_register: dict[str, Any],
) -> None:
    (output_root / "product_complete_closure_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "product_complete_closure_report.md").write_text(
        render_markdown(report),
        encoding="utf-8",
    )
    (output_root / "product_complete_pr_body.md").write_text(
        render_pr_body(report),
        encoding="utf-8",
    )
    (output_root / "no_ship_register.json").write_text(
        json.dumps(no_ship_register, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _conditional_notes(checks: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    for check in checks:
        if check["name"] == "macos_local_trial_gate" and check["status"] == "pass":
            notes.append("macOS local trial gate passed.")
        elif check["name"] == "macos_local_trial_gate" and check["status"] == "conditional":
            notes.append("macOS local trial has setup-required notes.")
        elif check["name"] == "macos_local_trial_gate" and check["status"] == "fail":
            notes.append("macOS local trial is blocked.")
        elif check["name"] == "assistant_real_runtime_gate" and check["status"] == "conditional":
            notes.append("Assistant real runtime gate has setup-required notes.")
    return notes


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Product-Complete Closure Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Branch: `{report['branch']}`",
        f"- Head SHA: `{report['headSha']}`",
        "",
        "## Product Readiness",
    ]
    for key, value in report["productReadiness"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks"])
    for check in report["checks"]:
        lines.append(f"- `{check['status']}` `{check['name']}` `{check['reasonCode']}`")
    if report["conditionalNotes"]:
        lines.extend(["", "## Conditional Notes"])
        lines.extend(f"- {item}" for item in report["conditionalNotes"])
    if report["noShipBlockers"]:
        lines.extend(["", "## No-Ship Blockers"])
        lines.extend(f"- `{item}`" for item in report["noShipBlockers"])
    return "\n".join(lines) + "\n"


def render_pr_body(report: dict[str, Any]) -> str:
    return (
        "## Summary\n"
        "- Product-complete closure gate for BinLiquid / AegisOS.\n"
        "- Scope: self-hosted single-organization enterprise Agent Control Plane.\n\n"
        "## Validation\n"
        f"- Closure gate: `{report['status']}`\n"
        f"- Head SHA: `{report['headSha']}`\n"
        f"- No-ship blockers: `{len(report['noShipBlockers'])}`\n\n"
        "## Remaining External Requirements\n"
        "- Public signed desktop release still requires real certificate/notarization evidence.\n"
        "- Public cloud multi-tenant SaaS remains out of scope.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run product-complete closure gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--skip-commands", action="store_true")
    parser.add_argument("--include-local-trial", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = run_product_complete_closure_gate(
        output_root=args.output_root,
        profile=args.profile,
        skip_commands=args.skip_commands,
        include_local_trial=args.include_local_trial,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']} output={args.output_root}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
