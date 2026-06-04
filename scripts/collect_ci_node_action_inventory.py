from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

KNOWN_NODE20_ACTIONS: dict[str, set[str]] = {
    "actions/checkout": {"v4"},
    "actions/setup-node": {"v4"},
    "actions/setup-python": {"v5"},
    "actions/upload-artifact": {"v4"},
    "actions/download-artifact": {"v4"},
    "pnpm/action-setup": {"v4"},
}


@dataclass(frozen=True)
class ActionUsage:
    workflow_file: str
    job_id: str
    step_name: str | None
    action: str
    ref: str
    runtime_known: bool
    node_runtime: str | None
    recommended_action: str
    is_blocker: bool


def collect_node_action_inventory(workflow_root: Path) -> list[ActionUsage]:
    if not workflow_root.exists():
        raise FileNotFoundError(f"workflow root does not exist: {workflow_root}")

    usages: list[ActionUsage] = []
    for workflow in sorted(workflow_root.glob("*.y*ml")):
        usages.extend(_collect_workflow_actions(workflow, workflow_root))
    return usages


def _collect_workflow_actions(workflow: Path, workflow_root: Path) -> list[ActionUsage]:
    usages: list[ActionUsage] = []
    job_id = "unknown"
    step_name: str | None = None
    in_jobs = False
    for raw_line in workflow.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs:
            job_match = re.match(r"^\s{2}([A-Za-z0-9_-]+):\s*$", line)
            if job_match:
                job_id = job_match.group(1)
                step_name = None
        name_match = re.match(r"^\s*-\s+name:\s*(.+?)\s*$", line)
        if name_match:
            step_name = _strip_quotes(name_match.group(1))
            continue
        uses_match = re.match(r"^\s*(?:-\s+)?uses:\s*(.+?)\s*$", line)
        if not uses_match:
            continue
        action_ref = _strip_quotes(uses_match.group(1))
        action, ref = _split_action_ref(action_ref)
        runtime_known, node_runtime, recommended_action, is_blocker = _classify_action(action, ref)
        usages.append(
            ActionUsage(
                workflow_file=str(workflow.relative_to(workflow_root.parent)),
                job_id=job_id,
                step_name=step_name,
                action=action,
                ref=ref,
                runtime_known=runtime_known,
                node_runtime=node_runtime,
                recommended_action=recommended_action,
                is_blocker=is_blocker,
            )
        )
        step_name = None
    return usages


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    return value


def _split_action_ref(value: str) -> tuple[str, str]:
    if value.startswith("./") or value.startswith("docker://"):
        return value, ""
    if "@" not in value:
        return value, ""
    action, ref = value.rsplit("@", 1)
    return action, ref


def _classify_action(action: str, ref: str) -> tuple[bool, str | None, str, bool]:
    if action.startswith("./"):
        return True, None, "none_local_action", False
    if action.startswith("docker://"):
        return True, None, "none_docker_action", False
    known_refs = KNOWN_NODE20_ACTIONS.get(action)
    if known_refs and ref in known_refs:
        return True, "node20", "review_node24_compatible_release", False
    if action.startswith("actions/"):
        return False, None, "review_official_action_runtime", False
    return False, None, "review_third_party_action_runtime", False


def write_node_action_inventory_report(
    usages: list[ActionUsage],
    output_root: Path,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "control-plane.ci-node-action-inventory/v1",
        "generatedAtUtc": datetime.now(UTC).isoformat(),
        "status": "pass" if not any(item.is_blocker for item in usages) else "blocked",
        "node20WarningPresent": any(item.node_runtime == "node20" for item in usages),
        "blockerCount": sum(1 for item in usages if item.is_blocker),
        "actionCount": len(usages),
        "actions": [asdict(item) for item in usages],
        "policy": {
            "warningOnlyChecksPass": "non_blocking",
            "unmaintainedSecurityRisk": "blocker",
            "actualNodeRuntimeFailure": "blocker",
        },
    }
    json_path = output_root / "node-action-inventory.json"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path = output_root / "NODE_ACTION_INVENTORY.md"
    markdown_path.write_text(_markdown(payload), encoding="utf-8")
    return json_path


def _markdown(payload: dict[str, object]) -> str:
    actions = payload.get("actions", [])
    rows = [
        "# CI Node Action Inventory",
        "",
        f"Generated: {payload['generatedAtUtc']}",
        f"Status: {payload['status']}",
        f"Action count: {payload['actionCount']}",
        f"Node 20 warning present: {payload['node20WarningPresent']}",
        "",
        "| Workflow | Job | Step | Action | Ref | Runtime | Recommendation | Blocker |",
        "|---|---|---|---|---|---|---|---:|",
    ]
    if isinstance(actions, list):
        for item in actions:
            if not isinstance(item, dict):
                continue
            rows.append(
                (
                    "| {workflow_file} | {job_id} | {step_name} | {action} | "
                    "{ref} | {node_runtime} | {recommended_action} | {is_blocker} |"
                ).format(
                    workflow_file=item.get("workflow_file", ""),
                    job_id=item.get("job_id", ""),
                    step_name=item.get("step_name") or "",
                    action=item.get("action", ""),
                    ref=item.get("ref", ""),
                    node_runtime=item.get("node_runtime") or "unknown",
                    recommended_action=item.get("recommended_action", ""),
                    is_blocker=item.get("is_blocker", False),
                )
            )
    rows.extend(
        [
            "",
            (
                "Policy: Node 20 deprecation warnings are not release blockers while "
                "checks pass. Actual runtime failure or an unmaintained action with a "
                "security risk is a blocker."
            ),
        ]
    )
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-root", default=".github/workflows")
    parser.add_argument("--output-root", default="artifacts/ci")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    usages = collect_node_action_inventory(Path(args.workflow_root))
    report_path = write_node_action_inventory_report(usages, Path(args.output_root))
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif payload["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
