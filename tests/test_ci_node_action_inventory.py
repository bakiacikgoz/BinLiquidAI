from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.collect_ci_node_action_inventory import (
    collect_node_action_inventory,
    write_node_action_inventory_report,
)


def test_collect_node_action_inventory_classifies_actions(tmp_path: Path) -> None:
    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "ci.yml").write_text(
        """
name: CI
on: [push]
jobs:
  test:
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - name: Local action
        uses: ./.github/actions/local
      - name: Docker action
        uses: docker://alpine:3.20
      - name: Third party
        uses: pnpm/action-setup@v4
""",
        encoding="utf-8",
    )

    usages = collect_node_action_inventory(workflow_root)

    assert len(usages) == 5
    assert usages[0].workflow_file == "workflows/ci.yml"
    assert usages[0].job_id == "test"
    assert usages[0].step_name == "Checkout"
    assert usages[0].action == "actions/checkout"
    assert usages[0].ref == "v4"
    assert usages[0].runtime_known is True
    assert usages[0].node_runtime == "node20"
    assert usages[0].recommended_action == "review_node24_compatible_release"
    assert usages[2].recommended_action == "none_local_action"
    assert usages[3].recommended_action == "none_docker_action"
    assert usages[4].action == "pnpm/action-setup"
    assert usages[4].node_runtime == "node20"
    assert not any(item.is_blocker for item in usages)


def test_write_node_action_inventory_report(tmp_path: Path) -> None:
    workflow_root = tmp_path / ".github" / "workflows"
    workflow_root.mkdir(parents=True)
    (workflow_root / "operator-panel.yml").write_text(
        """
jobs:
  operator-panel:
    steps:
      - uses: actions/upload-artifact@v4
""",
        encoding="utf-8",
    )
    usages = collect_node_action_inventory(workflow_root)
    report_path = write_node_action_inventory_report(usages, tmp_path / "artifacts" / "ci")
    payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["version"] == "control-plane.ci-node-action-inventory/v1"
    assert payload["status"] == "pass"
    assert payload["node20WarningPresent"] is True
    assert (report_path.parent / "NODE_ACTION_INVENTORY.md").exists()
