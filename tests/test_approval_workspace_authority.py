from __future__ import annotations

import hashlib

import pytest

from imperaos.governance.approval_store import ApprovalStore


def _ticket(store: ApprovalStore, workspace_id: str, key: str):
    snapshot = {"workspaceId": workspace_id, "kind": "task"}
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return store.create_ticket(
        workspace_id=workspace_id,
        run_id=f"run-{key}",
        target_kind="task",
        target_ref="chat",
        action_hash=digest,
        policy_hash=digest,
        request_hash=digest,
        snapshot_hash=digest,
        snapshot=snapshot,
        ttl_seconds=900,
        idempotency_key=key,
    )


def test_store_hides_foreign_ticket_for_pending_get_decide_and_execute(tmp_path) -> None:
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    local = _ticket(store, "workspace-a", "local")
    foreign = _ticket(store, "workspace-b", "foreign")

    assert [item.approval_id for item in store.list_pending(workspace_id="workspace-a")] == [
        local.approval_id
    ]
    assert store.get(foreign.approval_id, workspace_id="workspace-a") is None
    decision = store.decide(
        approval_id=foreign.approval_id,
        workspace_id="workspace-a",
        approve=True,
        actor="user-a",
        reason="should not exist",
    )
    execution = store.mark_executed(
        approval_id=foreign.approval_id,
        workspace_id="workspace-a",
        executed_by="user-a",
    )
    assert decision.error_code == execution.error_code == "APPROVAL_NOT_FOUND"
    assert store.get(foreign.approval_id, workspace_id="workspace-b").status.value == "pending"


def test_execute_persists_verified_executor_separately_from_decider(tmp_path) -> None:
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    ticket = _ticket(store, "workspace-a", "execute")
    assert store.decide(
        approval_id=ticket.approval_id,
        workspace_id="workspace-a",
        approve=True,
        actor="reviewer-a",
        reason="approved",
    ).error_code is None
    executed = store.mark_executed(
        approval_id=ticket.approval_id,
        workspace_id="workspace-a",
        executed_by="executor-a",
    )
    assert executed.error_code is None
    assert executed.ticket.actor == "reviewer-a"
    assert executed.ticket.executed_by == "executor-a"


def test_artifact_ticket_rejects_conflicting_workspace_bindings(tmp_path) -> None:
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    digest = "a" * 64
    with pytest.raises(ValueError, match="workspace binding"):
        store.create_ticket(
            workspace_id="workspace-a",
            run_id="run-conflict",
            target_kind="artifact_mutation_proposal",
            target_ref="workspace-b:artifact-1:proposal-1",
            action_hash=digest,
            policy_hash=digest,
            request_hash=digest,
            snapshot_hash=digest,
            snapshot={"workspaceId": "workspace-a"},
            ttl_seconds=900,
            idempotency_key="conflict",
        )
