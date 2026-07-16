from __future__ import annotations

from typing import Annotated

from pydantic import Field, JsonValue, StringConstraints

from imperaos.artifacts.models import (
    ArtifactDataClass,
    ArtifactKind,
    ArtifactModel,
    ArtifactMutationType,
    ArtifactStatus,
    BoundedId,
)


class CreateArtifactCommand(ArtifactModel):
    artifact_id: BoundedId | None = None
    kind: ArtifactKind = Field(strict=False)
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    data_class: ArtifactDataClass = Field(strict=False)
    content: dict[str, JsonValue]
    idempotency_key: BoundedId
    source_session_id: BoundedId | None = None
    source_turn_id: BoundedId | None = None
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class GetArtifactQuery(ArtifactModel):
    artifact_id: BoundedId
    revision_id: BoundedId | None = None


class ListArtifactsQuery(ArtifactModel):
    kind: ArtifactKind | None = Field(default=None, strict=False)
    status: ArtifactStatus | None = Field(default=None, strict=False)
    cursor: Annotated[str | None, StringConstraints(max_length=128, strict=True)] = None
    limit: int = Field(default=50, ge=1, le=200)


class MutateArtifactCommand(ArtifactModel):
    artifact_id: BoundedId
    expected_revision_number: int = Field(ge=1)
    mutation_type: ArtifactMutationType = Field(strict=False)
    content: dict[str, JsonValue]
    idempotency_key: BoundedId
    change_summary: Annotated[str, StringConstraints(max_length=500, strict=True)] = ""
    approval_granted: bool = False
    proposal_id: BoundedId | None = None


class ProposeArtifactMutationCommand(ArtifactModel):
    proposal_id: BoundedId | None = None
    artifact_id: BoundedId
    base_revision_number: int = Field(ge=1)
    mutation_type: ArtifactMutationType = Field(strict=False)
    content: dict[str, JsonValue]
    idempotency_key: BoundedId
    summary: Annotated[str, StringConstraints(max_length=500, strict=True)] = ""


class ApplyArtifactProposalCommand(ArtifactModel):
    proposal_id: BoundedId
    expected_revision_number: int = Field(ge=1)
    approval_granted: bool = False


class ArtifactHistoryQuery(ArtifactModel):
    artifact_id: BoundedId
    cursor: Annotated[str | None, StringConstraints(max_length=128, strict=True)] = None
    limit: int = Field(default=100, ge=1, le=500)


class RestoreArtifactCommand(ArtifactModel):
    artifact_id: BoundedId
    source_revision_id: BoundedId
    expected_revision_number: int = Field(ge=1)
    idempotency_key: BoundedId
    change_summary: Annotated[str, StringConstraints(max_length=500, strict=True)] = ""


class ArchiveArtifactCommand(ArtifactModel):
    artifact_id: BoundedId
    expected_revision_number: int = Field(ge=1)


class DuplicateArtifactCommand(ArtifactModel):
    source_artifact_id: BoundedId
    artifact_id: BoundedId | None = None
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    idempotency_key: BoundedId
