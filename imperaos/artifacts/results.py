from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from imperaos.artifacts.content import ArtifactContent
from imperaos.artifacts.models import ArtifactDescriptor, ArtifactRevisionDescriptor


@dataclass(frozen=True, slots=True)
class ArtifactOperationResult:
    artifact: ArtifactDescriptor
    revision: ArtifactRevisionDescriptor
    created: bool
    disposition: Literal["created", "no_op", "idempotent_replay", "updated"]


@dataclass(frozen=True, slots=True)
class ArtifactReadResult:
    artifact: ArtifactDescriptor
    revision: ArtifactRevisionDescriptor
    content: ArtifactContent


@dataclass(frozen=True, slots=True)
class ArtifactListResult:
    items: tuple[ArtifactDescriptor, ...]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactHistoryResult:
    items: tuple[ArtifactRevisionDescriptor, ...]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactMutationProposalResult:
    proposal_id: str
    artifact_id: str
    base_revision_number: int
    status: Literal["pending", "applied", "rejected", "stale"]
    content_sha256: str
    summary: str
