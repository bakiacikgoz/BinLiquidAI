from __future__ import annotations

from pathlib import Path

from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence
from binliquid.local_product.target_closure import build_target_closure_actions


def test_target_actions_for_missing_targets_have_safe_commands(tmp_path: Path) -> None:
    reconciliation = reconcile_platform_evidence(
        store_root=tmp_path / "missing",
        current_commit="a" * 40,
    )

    actions = build_target_closure_actions(reconciliation=reconciliation, head_sha="a" * 40)

    assert {action.target for action in actions} >= {"darwin-arm64", "linux-x64"}
    for action in actions:
        assert Path(action.runbook).exists()
        joined = " ".join(action.commands).lower()
        assert "github_token" not in joined
        assert "secret" not in joined
        assert action.commands

