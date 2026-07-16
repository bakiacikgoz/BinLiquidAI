from __future__ import annotations

from pathlib import Path

import pytest

from imperaos.artifacts.commands import (
    ApplyArtifactProposalCommand,
    ArchiveArtifactCommand,
    ArtifactHistoryQuery,
    CreateArtifactCommand,
    DuplicateArtifactCommand,
    GetArtifactQuery,
    ListArtifactsQuery,
    MutateArtifactCommand,
    ProposeArtifactMutationCommand,
    RestoreArtifactCommand,
)
from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.models import (
    ArtifactDataClass,
    ArtifactKind,
    ArtifactMutationType,
    ArtifactStatus,
    OperationContext,
    PrincipalType,
)
from imperaos.artifacts.service import ArtifactService


def document(text: str) -> dict[str, object]:
    return {
        "kind": "document",
        "schemaVersion": 1,
        "language": "tr",
        "pageMode": "document",
        "blocks": [
            {
                "id": "block-1",
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def user_context(*roles: str) -> OperationContext:
    return OperationContext(
        workspace_id="workspace-1",
        principal_type=PrincipalType.USER,
        principal_id="user-1",
        roles=roles or ("artifact_editor",),
        request_id="request-1",
    )


def assistant_context() -> OperationContext:
    return OperationContext(
        workspace_id="workspace-1",
        principal_type=PrincipalType.ASSISTANT,
        principal_id="assistant-1",
        roles=("artifact_editor",),
        request_id="request-ai-1",
    )


def create_command(*, key: str = "create-1") -> CreateArtifactCommand:
    return CreateArtifactCommand(
        artifact_id="artifact-1",
        kind=ArtifactKind.DOCUMENT,
        title="Operations plan",
        data_class=ArtifactDataClass.INTERNAL,
        content=document("v1"),
        idempotency_key=key,
    )


def test_document_service_create_get_list_and_create_idempotency(tmp_path: Path) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    context = user_context()

    created = service.create(create_command(), context)
    replay = service.create(create_command(), context)
    loaded = service.get(GetArtifactQuery(artifact_id="artifact-1"), context)
    listed = service.list(ListArtifactsQuery(limit=20), context)

    assert created.created is True
    assert replay.created is False
    assert replay.disposition == "idempotent_replay"
    assert loaded.artifact == created.artifact
    assert loaded.content.model_dump(mode="json", by_alias=True) == document("v1")
    assert listed.items == (created.artifact,)


def test_document_service_mutate_history_conflict_and_restore(tmp_path: Path) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    context = user_context()
    created = service.create(create_command(), context)
    mutated = service.mutate(
        MutateArtifactCommand(
            artifact_id="artifact-1",
            expected_revision_number=1,
            mutation_type=ArtifactMutationType.REPLACE_CONTENT,
            content=document("v2"),
            idempotency_key="mutate-2",
        ),
        context,
    )

    with pytest.raises(ArtifactDomainError) as stale:
        service.mutate(
            MutateArtifactCommand(
                artifact_id="artifact-1",
                expected_revision_number=1,
                mutation_type=ArtifactMutationType.REPLACE_CONTENT,
                content=document("stale-secret-marker"),
                idempotency_key="mutate-stale",
            ),
            context,
        )

    restored = service.restore(
        RestoreArtifactCommand(
            artifact_id="artifact-1",
            source_revision_id=created.revision.revision_id,
            expected_revision_number=2,
            idempotency_key="restore-3",
        ),
        context,
    )
    history = service.history(ArtifactHistoryQuery(artifact_id="artifact-1"), context)

    assert mutated.artifact.current_revision_number == 2
    assert stale.value.code is ArtifactErrorCode.ARTIFACT_REVISION_CONFLICT
    assert "stale-secret-marker" not in str(stale.value)
    assert restored.artifact.current_revision_number == 3
    assert [item.revision_number for item in history.items] == [1, 2, 3]


def test_document_service_ai_proposal_is_approval_bound_and_applies_new_revision(
    tmp_path: Path,
) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    service.create(create_command(), user_context())
    assistant = assistant_context()
    proposal = service.propose_mutation(
        ProposeArtifactMutationCommand(
            proposal_id="proposal-1",
            artifact_id="artifact-1",
            base_revision_number=1,
            mutation_type=ArtifactMutationType.REPLACE_CONTENT,
            content=document("AI proposal"),
            idempotency_key="proposal-key-1",
            summary="Update opening paragraph",
        ),
        assistant,
    )

    with pytest.raises(ArtifactDomainError) as approval_required:
        service.apply_proposal(
            ApplyArtifactProposalCommand(
                proposal_id="proposal-1",
                expected_revision_number=1,
                approval_granted=False,
            ),
            assistant,
        )
    applied = service.apply_proposal(
        ApplyArtifactProposalCommand(
            proposal_id="proposal-1",
            expected_revision_number=1,
            approval_granted=True,
        ),
        assistant,
    )

    assert proposal.status == "pending"
    assert approval_required.value.code is ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED
    assert applied.artifact.current_revision_number == 2


def test_document_service_duplicate_and_archive_are_workspace_scoped(tmp_path: Path) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    admin = user_context("artifact_admin")
    service.create(create_command(), admin)
    duplicated = service.duplicate(
        DuplicateArtifactCommand(
            source_artifact_id="artifact-1",
            artifact_id="artifact-2",
            title="Operations plan copy",
            idempotency_key="duplicate-1",
        ),
        admin,
    )
    archived = service.archive(
        ArchiveArtifactCommand(
            artifact_id="artifact-1",
            expected_revision_number=1,
        ),
        admin,
    )
    with pytest.raises(ArtifactDomainError) as archived_restore:
        service.restore(
            RestoreArtifactCommand(
                artifact_id="artifact-1",
                source_revision_id=archived.revision.revision_id,
                expected_revision_number=1,
                idempotency_key="restore-archived",
            ),
            admin,
        )
    with pytest.raises(ArtifactDomainError) as archived_mutation:
        service.mutate(
            MutateArtifactCommand(
                artifact_id="artifact-1",
                expected_revision_number=1,
                mutation_type=ArtifactMutationType.REPLACE_CONTENT,
                content=document("must remain archived"),
                idempotency_key="mutate-archived",
            ),
            admin,
        )

    assert duplicated.artifact.artifact_id == "artifact-2"
    assert duplicated.artifact.current_revision_number == 1
    assert archived.artifact.status is ArtifactStatus.ARCHIVED
    assert archived_restore.value.code is ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED
    assert archived_mutation.value.code is ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED
    assert service.get(GetArtifactQuery(artifact_id="artifact-2"), admin).content is not None


def test_document_service_revalidates_schema_without_leaking_raw_content_in_error(
    tmp_path: Path,
) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    command = create_command()
    invalid = command.model_copy(
        update={"content": {"kind": "document", "secret": "raw-secret-marker"}}
    )

    with pytest.raises(ArtifactDomainError) as caught:
        service.create(invalid, user_context())

    assert caught.value.code is ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID
    assert "raw-secret-marker" not in str(caught.value)
