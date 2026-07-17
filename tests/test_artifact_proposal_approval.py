from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.models import OperationContext, PrincipalType
from imperaos.artifacts.proposal_approval import ArtifactProposalApprovalGateway
from imperaos.cli import _require_approval_workspace
from imperaos.governance.approval_store import ApprovalStore


def test_artifact_approval_decision_is_bound_to_the_trusted_workspace() -> None:
    ticket = SimpleNamespace(
        target_kind="artifact_mutation_proposal",
        target_ref="workspace-1:artifact-1",
        snapshot={"workspace_id": "workspace-1"},
    )

    _require_approval_workspace(ticket, "workspace-1", "approval-1")
    with pytest.raises(typer.Exit):
        _require_approval_workspace(ticket, "workspace-2", "approval-1")


def test_proposal_approval_rejects_missing_provenance_before_creating_ticket(
    tmp_path: Path,
) -> None:
    store = ApprovalStore(tmp_path / "approvals.sqlite3")
    gateway = ArtifactProposalApprovalGateway(store)
    row = {
        "workspace_id": "workspace-1",
        "artifact_id": "artifact-1",
        "proposal_id": "legacy-proposal",
        "base_revision_number": 1,
        "mutation_type": "replace_content",
        "content_sha256": "a" * 64,
        "request_sha256": None,
        "context_sha256": None,
        "selection_sha256": None,
        "source_session_id": None,
        "source_turn_id": None,
        "trace_id": None,
        "proposed_by_id": "assistant-1",
        "idempotency_key": "legacy-key",
    }
    context = OperationContext(
        workspace_id="workspace-1",
        principal_type=PrincipalType.ASSISTANT,
        principal_id="assistant-1",
        roles=("artifact_editor",),
        request_id="request-1",
    )

    with pytest.raises(ArtifactDomainError) as caught:
        gateway.request_approval(row, context)

    assert caught.value.code is ArtifactErrorCode.ARTIFACT_POLICY_UNAVAILABLE
    assert store.list_pending() == []
