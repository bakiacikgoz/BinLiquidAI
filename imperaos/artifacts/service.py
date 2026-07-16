from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from imperaos.artifacts.commands import (
    ApplyArtifactProposalCommand,
    ArchiveArtifactCommand,
    ArtifactHistoryQuery,
    BeginArtifactExportCommand,
    CancelArtifactExportCommand,
    CommitArtifactExportCommand,
    CreateArtifactCommand,
    DuplicateArtifactCommand,
    GetArtifactQuery,
    ListArtifactsQuery,
    MutateArtifactCommand,
    ProposeArtifactMutationCommand,
    RestoreArtifactCommand,
    SubmitArtifactFormCommand,
)
from imperaos.artifacts.content import ArtifactContent, FormContentV1, validate_artifact_content
from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.exports import (
    DEFAULT_ARTIFACT_EXPORT_MAX_BYTES,
    canonical_export_basename,
    require_export_format,
)
from imperaos.artifacts.evidence import (
    ArtifactEvidenceRecorder,
    record_artifact_evidence,
)
from imperaos.artifacts.form_continuation import ArtifactFormContinuationGateway
from imperaos.artifacts.forms import validate_form_response
from imperaos.artifacts.models import (
    ArtifactDescriptor,
    ArtifactKind,
    ArtifactModel,
    ArtifactMutationType,
    ArtifactRevisionDescriptor,
    ArtifactStatus,
    OperationContext,
    canonical_json,
)
from imperaos.artifacts.policy import ArtifactPermission, ArtifactPolicyGateway
from imperaos.artifacts.results import (
    ArtifactExportBeginResult,
    ArtifactExportResult,
    ArtifactFormSubmissionResult,
    ArtifactHistoryResult,
    ArtifactListResult,
    ArtifactMutationProposalResult,
    ArtifactOperationResult,
    ArtifactReadResult,
)
from imperaos.artifacts.store import ArtifactStore, revision_content_relpath
from imperaos.governance.approval_store import ApprovalStore
from imperaos.runtime.paths import state_path

_DEFAULT_CONTINUATION_GATEWAY = object()


class ArtifactService:
    """Policy-enforced application service for governed artifact operations."""

    def __init__(
        self,
        root: str | Path,
        *,
        policy: ArtifactPolicyGateway | None = None,
        evidence: ArtifactEvidenceRecorder | None = None,
        continuation_gateway: ArtifactFormContinuationGateway | None | object = (
            _DEFAULT_CONTINUATION_GATEWAY
        ),
    ) -> None:
        self.store = ArtifactStore(root)
        self.policy = policy or ArtifactPolicyGateway()
        self.evidence = evidence or ArtifactEvidenceRecorder(self.store.database_path)
        self._continuation_gateway = continuation_gateway

    @record_artifact_evidence("artifact.create")
    def create(
        self,
        command: CreateArtifactCommand,
        context: OperationContext,
    ) -> ArtifactOperationResult:
        self.policy.authorize(ArtifactPermission.CREATE, context)
        request_hash = self._request_hash(command)
        replay = self._load_operation_replay(
            context.workspace_id,
            command.idempotency_key,
            "create",
            request_hash,
        )
        if replay is not None:
            return replay

        content = self._validate_content(command.kind, command.content)
        payload = canonical_json(content).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        artifact_id = command.artifact_id or self._stable_id(
            "artifact", context.workspace_id, command.idempotency_key
        )
        revision_id = self._stable_id("revision", artifact_id, command.idempotency_key)
        now = datetime.now(UTC)
        revision = ArtifactRevisionDescriptor(
            revision_id=revision_id,
            artifact_id=artifact_id,
            revision_number=1,
            schema_version=content.schema_version,
            mutation_type=ArtifactMutationType.CREATE,
            content_relpath=revision_content_relpath(
                context.workspace_id, artifact_id, 1, revision_id, "json"
            ),
            content_sha256=digest,
            content_size_bytes=len(payload),
            content_encoding="json",
            change_summary="Artifact created",
            author_type=context.principal_type,
            author_id=context.principal_id,
            idempotency_key=command.idempotency_key,
            created_at_utc=now,
        )
        artifact = ArtifactDescriptor(
            artifact_id=artifact_id,
            workspace_id=context.workspace_id,
            kind=command.kind,
            title=command.title,
            status=ArtifactStatus.DRAFT,
            schema_version=content.schema_version,
            data_class=command.data_class,
            current_revision_id=revision_id,
            current_revision_number=1,
            source_session_id=command.source_session_id,
            source_turn_id=command.source_turn_id,
            created_by_type=context.principal_type,
            created_by_id=context.principal_id,
            updated_by_id=context.principal_id,
            created_at_utc=now,
            updated_at_utc=now,
            etag=digest,
            metadata=command.metadata,
        )
        result = self.store.create_artifact(
            artifact,
            revision,
            payload,
            operation="create",
            request_hash=request_hash,
        )
        operation = ArtifactOperationResult(
            artifact=result.artifact,
            revision=result.revision,
            created=result.created,
            disposition=result.disposition,
        )
        return operation

    @record_artifact_evidence("artifact.get")
    def get(
        self,
        query: GetArtifactQuery,
        context: OperationContext,
    ) -> ArtifactReadResult:
        artifact = self.store.get_artifact(context.workspace_id, query.artifact_id)
        self.policy.authorize(
            ArtifactPermission.READ,
            context,
            artifact_workspace_id=artifact.workspace_id,
        )
        revision = self.store.get_revision(
            context.workspace_id,
            query.artifact_id,
            query.revision_id or artifact.current_revision_id,
        )
        content = self._decode_content(
            artifact.kind, revision.content, schema_version=revision.descriptor.schema_version
        )
        return ArtifactReadResult(artifact, revision.descriptor, content)

    @record_artifact_evidence("artifact.list")
    def list(
        self,
        query: ListArtifactsQuery,
        context: OperationContext,
    ) -> ArtifactListResult:
        self.policy.authorize(ArtifactPermission.READ, context)
        offset = self._decode_cursor(query.cursor)
        items = self.store.list_artifacts(
            context.workspace_id,
            kind=query.kind.value if query.kind else None,
            status=query.status.value if query.status else None,
            limit=query.limit + 1,
            offset=offset,
        )
        has_more = len(items) > query.limit
        return ArtifactListResult(
            items=items[: query.limit],
            next_cursor=str(offset + query.limit) if has_more else None,
        )

    @record_artifact_evidence("artifact.mutate")
    def mutate(
        self,
        command: MutateArtifactCommand,
        context: OperationContext,
    ) -> ArtifactOperationResult:
        current = self.store.get_artifact(context.workspace_id, command.artifact_id)
        permission = (
            ArtifactPermission.AI_APPLY
            if context.principal_type.value == "assistant"
            else ArtifactPermission.UPDATE
        )
        self.policy.authorize(
            permission,
            context,
            artifact_workspace_id=current.workspace_id,
            current_data_class=current.data_class,
            target_data_class=current.data_class,
            approval_granted=command.approval_granted,
        )
        request_hash = self._request_hash(command)
        replay = self._load_operation_replay(
            context.workspace_id,
            command.idempotency_key,
            "mutate",
            request_hash,
        )
        if replay is not None:
            return replay
        if current.status is ArtifactStatus.ARCHIVED:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED,
                "archived artifacts are read-only",
            )
        if permission is ArtifactPermission.AI_APPLY and command.proposal_id is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED,
                "assistant mutations require an approved proposal",
            )

        content = self._validate_content(
            current.kind, command.content, schema_version=current.schema_version
        )
        payload = canonical_json(content).encode("utf-8")
        revision_number = command.expected_revision_number + 1
        revision_id = self._stable_id(
            "revision", current.artifact_id, command.idempotency_key
        )
        digest = hashlib.sha256(payload).hexdigest()
        now = datetime.now(UTC)
        revision = ArtifactRevisionDescriptor(
            revision_id=revision_id,
            artifact_id=current.artifact_id,
            parent_revision_id=current.current_revision_id,
            revision_number=revision_number,
            schema_version=current.schema_version,
            mutation_type=command.mutation_type,
            content_relpath=revision_content_relpath(
                context.workspace_id,
                current.artifact_id,
                revision_number,
                revision_id,
                "json",
            ),
            content_sha256=digest,
            content_size_bytes=len(payload),
            content_encoding="json",
            change_summary=command.change_summary,
            author_type=context.principal_type,
            author_id=context.principal_id,
            idempotency_key=command.idempotency_key,
            created_at_utc=now,
        )
        updated = ArtifactDescriptor.model_validate(
            {
                **current.model_dump(mode="python"),
                "current_revision_id": revision_id,
                "current_revision_number": revision_number,
                "updated_by_id": context.principal_id,
                "updated_at_utc": now,
                "etag": digest,
            }
        )
        stored = self.store.append_revision(
            updated,
            revision,
            payload,
            expected_revision_number=command.expected_revision_number,
            operation="mutate",
            request_hash=request_hash,
        )
        operation = ArtifactOperationResult(
            stored.artifact,
            stored.revision,
            stored.created,
            stored.disposition,
        )
        return operation

    @record_artifact_evidence("artifact.propose_mutation")
    def propose_mutation(
        self,
        command: ProposeArtifactMutationCommand,
        context: OperationContext,
    ) -> ArtifactMutationProposalResult:
        artifact = self.store.get_artifact(context.workspace_id, command.artifact_id)
        self.policy.authorize(
            ArtifactPermission.AI_PROPOSE,
            context,
            artifact_workspace_id=artifact.workspace_id,
        )
        content = self._validate_content(
            artifact.kind, command.content, schema_version=artifact.schema_version
        )
        content_json = canonical_json(content)
        digest = hashlib.sha256(content_json.encode("utf-8")).hexdigest()
        proposal_id = command.proposal_id or self._stable_id(
            "proposal", command.artifact_id, command.idempotency_key
        )
        now = datetime.now(UTC).isoformat()
        with self.store._connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM artifact_mutation_proposals
                WHERE artifact_id = ? AND idempotency_key = ?
                """,
                (command.artifact_id, command.idempotency_key),
            ).fetchone()
            if existing is not None:
                if existing["content_sha256"] != digest:
                    self._raise_conflict("proposal idempotency payload mismatch")
                return self._proposal_result(existing)
            if artifact.current_revision_number != command.base_revision_number:
                self._raise_conflict("proposal base revision is stale")
            try:
                connection.execute(
                    """
                    INSERT INTO artifact_mutation_proposals (
                        proposal_id, workspace_id, artifact_id, base_revision_number,
                        mutation_type, content_json, content_sha256, idempotency_key,
                        summary, proposed_by_id, status, created_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        proposal_id,
                        context.workspace_id,
                        command.artifact_id,
                        command.base_revision_number,
                        command.mutation_type.value,
                        content_json,
                        digest,
                        command.idempotency_key,
                        command.summary,
                        context.principal_id,
                        now,
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                raise ArtifactDomainError(
                    ArtifactErrorCode.ARTIFACT_REVISION_CONFLICT,
                    "proposal identity conflicts with an existing proposal",
                ) from exc
        return ArtifactMutationProposalResult(
            proposal_id,
            command.artifact_id,
            command.base_revision_number,
            "pending",
            digest,
            command.summary,
        )

    @record_artifact_evidence("artifact.apply_proposal")
    def apply_proposal(
        self,
        command: ApplyArtifactProposalCommand,
        context: OperationContext,
    ) -> ArtifactOperationResult:
        with self.store._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifact_mutation_proposals WHERE proposal_id = ?",
                (command.proposal_id,),
            ).fetchone()
        if row is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_NOT_FOUND,
                "artifact mutation proposal does not exist",
            )
        if row["workspace_id"] != context.workspace_id:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_WORKSPACE_MISMATCH,
                "proposal belongs to a different workspace",
            )
        artifact = self.store.get_artifact(context.workspace_id, row["artifact_id"])
        self.policy.authorize(
            ArtifactPermission.AI_APPLY,
            context,
            artifact_workspace_id=artifact.workspace_id,
            approval_granted=command.approval_granted,
        )
        if row["status"] == "applied" and row["applied_revision_id"]:
            stored = self.store.get_revision(
                context.workspace_id, artifact.artifact_id, row["applied_revision_id"]
            )
            return ArtifactOperationResult(
                artifact, stored.descriptor, False, "idempotent_replay"
            )
        if row["status"] != "pending":
            self._raise_conflict("proposal is not pending")

        result = self.mutate(
            MutateArtifactCommand(
                artifact_id=artifact.artifact_id,
                expected_revision_number=command.expected_revision_number,
                mutation_type=row["mutation_type"],
                content=json.loads(row["content_json"]),
                idempotency_key=row["idempotency_key"],
                change_summary=row["summary"],
                approval_granted=command.approval_granted,
                proposal_id=command.proposal_id,
            ),
            context,
        )
        with self.store._connect() as connection:
            connection.execute(
                """
                UPDATE artifact_mutation_proposals
                SET status = 'applied', applied_revision_id = ?, completed_at_utc = ?
                WHERE proposal_id = ? AND status = 'pending'
                """,
                (
                    result.revision.revision_id,
                    datetime.now(UTC).isoformat(),
                    command.proposal_id,
                ),
            )
            connection.commit()
        return result

    @record_artifact_evidence("artifact.history")
    def history(
        self,
        query: ArtifactHistoryQuery,
        context: OperationContext,
    ) -> ArtifactHistoryResult:
        artifact = self.store.get_artifact(context.workspace_id, query.artifact_id)
        self.policy.authorize(
            ArtifactPermission.READ,
            context,
            artifact_workspace_id=artifact.workspace_id,
        )
        offset = self._decode_cursor(query.cursor)
        revisions = self.store.list_revisions(context.workspace_id, query.artifact_id)
        page = revisions[offset : offset + query.limit + 1]
        has_more = len(page) > query.limit
        return ArtifactHistoryResult(
            items=page[: query.limit],
            next_cursor=str(offset + query.limit) if has_more else None,
        )

    @record_artifact_evidence("artifact.restore")
    def restore(
        self,
        command: RestoreArtifactCommand,
        context: OperationContext,
    ) -> ArtifactOperationResult:
        current = self.store.get_artifact(context.workspace_id, command.artifact_id)
        self.policy.authorize(
            ArtifactPermission.RESTORE,
            context,
            artifact_workspace_id=current.workspace_id,
        )
        request_hash = self._request_hash(command)
        replay = self._load_operation_replay(
            context.workspace_id,
            command.idempotency_key,
            "restore",
            request_hash,
        )
        if replay is not None:
            return replay
        if current.status is ArtifactStatus.ARCHIVED:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED,
                "archived artifacts are read-only",
            )
        source = self.store.get_revision(
            context.workspace_id, command.artifact_id, command.source_revision_id
        )
        content = self._decode_content(
            current.kind, source.content, schema_version=source.descriptor.schema_version
        )
        payload = canonical_json(content).encode("utf-8")
        revision_number = command.expected_revision_number + 1
        revision_id = self._stable_id(
            "revision", current.artifact_id, command.idempotency_key
        )
        digest = hashlib.sha256(payload).hexdigest()
        now = datetime.now(UTC)
        revision = ArtifactRevisionDescriptor(
            revision_id=revision_id,
            artifact_id=current.artifact_id,
            parent_revision_id=current.current_revision_id,
            base_revision_id=command.source_revision_id,
            revision_number=revision_number,
            schema_version=source.descriptor.schema_version,
            mutation_type=ArtifactMutationType.RESTORE,
            content_relpath=revision_content_relpath(
                context.workspace_id,
                current.artifact_id,
                revision_number,
                revision_id,
                "json",
            ),
            content_sha256=digest,
            content_size_bytes=len(payload),
            content_encoding="json",
            change_summary=command.change_summary,
            author_type=context.principal_type,
            author_id=context.principal_id,
            idempotency_key=command.idempotency_key,
            created_at_utc=now,
        )
        updated = ArtifactDescriptor.model_validate(
            {
                **current.model_dump(mode="python"),
                "current_revision_id": revision_id,
                "current_revision_number": revision_number,
                "schema_version": source.descriptor.schema_version,
                "updated_by_id": context.principal_id,
                "updated_at_utc": now,
                "etag": digest,
            }
        )
        stored = self.store.restore_revision(
            updated,
            revision,
            source_revision_id=command.source_revision_id,
            expected_revision_number=command.expected_revision_number,
            operation="restore",
            request_hash=request_hash,
        )
        operation = ArtifactOperationResult(
            stored.artifact,
            stored.revision,
            stored.created,
            stored.disposition,
        )
        return operation

    @record_artifact_evidence("artifact.archive")
    def archive(
        self,
        command: ArchiveArtifactCommand,
        context: OperationContext,
    ) -> ArtifactOperationResult:
        current = self.store.get_artifact(context.workspace_id, command.artifact_id)
        self.policy.authorize(
            ArtifactPermission.ARCHIVE,
            context,
            artifact_workspace_id=current.workspace_id,
        )
        now = datetime.now(UTC)
        archived = ArtifactDescriptor.model_validate(
            {
                **current.model_dump(mode="python"),
                "status": ArtifactStatus.ARCHIVED,
                "archived_at_utc": now,
                "updated_at_utc": now,
                "updated_by_id": context.principal_id,
            }
        )
        stored_artifact = self.store.update_artifact_metadata(
            archived,
            expected_revision_number=command.expected_revision_number,
        )
        revision = self.store.get_revision(
            context.workspace_id, current.artifact_id, current.current_revision_id
        ).descriptor
        return ArtifactOperationResult(stored_artifact, revision, False, "updated")

    @record_artifact_evidence("artifact.duplicate")
    def duplicate(
        self,
        command: DuplicateArtifactCommand,
        context: OperationContext,
    ) -> ArtifactOperationResult:
        source = self.store.get_artifact(
            context.workspace_id, command.source_artifact_id
        )
        self.policy.authorize(
            ArtifactPermission.DUPLICATE,
            context,
            artifact_workspace_id=source.workspace_id,
        )
        request_hash = self._request_hash(command)
        replay = self._load_operation_replay(
            context.workspace_id,
            command.idempotency_key,
            "duplicate",
            request_hash,
        )
        if replay is not None:
            return replay
        loaded = self.get(
            GetArtifactQuery(
                artifact_id=source.artifact_id,
                revision_id=command.source_revision_id,
            ),
            context,
        )
        content_input = (
            command.content_override
            if command.content_override is not None
            else loaded.content.model_dump(mode="json", by_alias=True)
        )
        content = self._validate_content(
            source.kind,
            content_input,
            schema_version=loaded.revision.schema_version,
        )
        payload = canonical_json(content).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        artifact_id = command.artifact_id or self._stable_id(
            "artifact", context.workspace_id, command.idempotency_key
        )
        revision_id = self._stable_id("revision", artifact_id, command.idempotency_key)
        now = datetime.now(UTC)
        revision = ArtifactRevisionDescriptor(
            revision_id=revision_id,
            artifact_id=artifact_id,
            base_revision_id=loaded.revision.revision_id,
            revision_number=1,
            schema_version=loaded.revision.schema_version,
            mutation_type=ArtifactMutationType.DUPLICATE,
            content_relpath=revision_content_relpath(
                context.workspace_id, artifact_id, 1, revision_id, "json"
            ),
            content_sha256=digest,
            content_size_bytes=len(payload),
            content_encoding="json",
            change_summary="Artifact duplicated",
            author_type=context.principal_type,
            author_id=context.principal_id,
            idempotency_key=command.idempotency_key,
            created_at_utc=now,
        )
        artifact = ArtifactDescriptor(
            artifact_id=artifact_id,
            workspace_id=context.workspace_id,
            kind=source.kind,
            title=command.title,
            status=ArtifactStatus.DRAFT,
            schema_version=loaded.revision.schema_version,
            data_class=source.data_class,
            current_revision_id=revision_id,
            current_revision_number=1,
            source_session_id=source.source_session_id,
            source_turn_id=source.source_turn_id,
            created_by_type=context.principal_type,
            created_by_id=context.principal_id,
            updated_by_id=context.principal_id,
            created_at_utc=now,
            updated_at_utc=now,
            etag=digest,
            metadata={
                **source.metadata,
                "forkedFromArtifactId": source.artifact_id,
                "forkedFromRevisionId": loaded.revision.revision_id,
            },
        )
        stored = self.store.create_duplicate_artifact(
            artifact,
            revision,
            payload,
            source_artifact_id=source.artifact_id,
            operation="duplicate",
            request_hash=request_hash,
        )
        operation = ArtifactOperationResult(
            artifact=stored.artifact,
            revision=stored.revision,
            created=stored.created,
            disposition=stored.disposition,
        )
        return operation

    @record_artifact_evidence("artifact.export.started")
    def begin_export(
        self,
        command: BeginArtifactExportCommand,
        context: OperationContext,
    ) -> ArtifactExportBeginResult:
        artifact = self.store.get_artifact(context.workspace_id, command.artifact_id)
        self.policy.authorize(
            ArtifactPermission.EXPORT,
            context,
            artifact_workspace_id=artifact.workspace_id,
            current_data_class=artifact.data_class,
            approval_granted=False,
        )
        if command.approval_id is not None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED,
                "artifact export approval cannot be asserted by the caller",
            )
        format_name = require_export_format(artifact.kind, command.format)
        stored_revision = self.store.get_revision(
            context.workspace_id,
            artifact.artifact_id,
            command.revision_id,
        )
        content = self._decode_content(
            artifact.kind,
            stored_revision.content,
            schema_version=stored_revision.descriptor.schema_version,
        )
        basename = canonical_export_basename(artifact, content, format_name)
        request_hash = self._request_hash(command)
        export_id = self._stable_id(
            "export", context.workspace_id, command.idempotency_key
        )
        record, created = self.store.create_export(
            export_id=export_id,
            workspace_id=context.workspace_id,
            artifact_id=artifact.artifact_id,
            revision_id=stored_revision.descriptor.revision_id,
            format_name=format_name,
            basename=basename,
            actor_type=context.principal_type.value,
            actor_id=context.principal_id,
            idempotency_key=command.idempotency_key,
            request_sha256=request_hash,
        )
        return ArtifactExportBeginResult(
            export_id=record.export_id,
            artifact_id=record.artifact_id,
            revision_id=record.revision_id,
            format=record.format,
            basename=record.basename,
            max_bytes=DEFAULT_ARTIFACT_EXPORT_MAX_BYTES,
            disposition="created" if created else "idempotent_replay",
        )

    @record_artifact_evidence("artifact.export.completed")
    def commit_export(
        self,
        command: CommitArtifactExportCommand,
        context: OperationContext,
    ) -> ArtifactExportResult:
        current = self.store.get_export(context.workspace_id, command.export_id)
        artifact = self.store.get_artifact(context.workspace_id, current.artifact_id)
        self.policy.authorize(
            ArtifactPermission.EXPORT,
            context,
            artifact_workspace_id=artifact.workspace_id,
            current_data_class=artifact.data_class,
            approval_granted=False,
        )
        if command.basename != current.basename:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_EXPORT_FAILED,
                "artifact export basename does not match the authorized record",
            )
        record, updated = self.store.transition_export(
            workspace_id=context.workspace_id,
            export_id=current.export_id,
            actor_type=context.principal_type.value,
            actor_id=context.principal_id,
            status="completed",
            basename=command.basename,
            sha256=command.sha256,
            size_bytes=command.size_bytes,
            reason_code=None,
            idempotency_key=command.idempotency_key,
            request_sha256=self._request_hash(command),
        )
        return ArtifactExportResult(
            export_id=record.export_id,
            artifact_id=record.artifact_id,
            revision_id=record.revision_id,
            format=record.format,
            status=record.status,
            basename=record.basename,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            reason_code=record.reason_code,
            disposition="updated" if updated else "idempotent_replay",
        )

    @record_artifact_evidence("artifact.export.cancelled")
    def cancel_export(
        self,
        command: CancelArtifactExportCommand,
        context: OperationContext,
    ) -> ArtifactExportResult:
        current = self.store.get_export(context.workspace_id, command.export_id)
        artifact = self.store.get_artifact(context.workspace_id, current.artifact_id)
        self.policy.authorize(
            ArtifactPermission.EXPORT,
            context,
            artifact_workspace_id=artifact.workspace_id,
            current_data_class=artifact.data_class,
            approval_granted=False,
        )
        status = "failed" if command.reason != "user_cancelled" else "cancelled"
        record, updated = self.store.transition_export(
            workspace_id=context.workspace_id,
            export_id=current.export_id,
            actor_type=context.principal_type.value,
            actor_id=context.principal_id,
            status=status,
            basename=current.basename,
            sha256=None,
            size_bytes=None,
            reason_code=command.reason,
            idempotency_key=command.idempotency_key,
            request_sha256=self._request_hash(command),
        )
        return ArtifactExportResult(
            export_id=record.export_id,
            artifact_id=record.artifact_id,
            revision_id=record.revision_id,
            format=record.format,
            status=record.status,
            basename=record.basename,
            sha256=record.sha256,
            size_bytes=record.size_bytes,
            reason_code=record.reason_code,
            disposition="updated" if updated else "idempotent_replay",
        )

    @record_artifact_evidence("artifact.form.submitted")
    def submit_form(
        self,
        command: SubmitArtifactFormCommand,
        context: OperationContext,
    ) -> ArtifactFormSubmissionResult:
        if command.persistence_policy != "none":
            raise ArtifactDomainError(
                ArtifactErrorCode.FORM_SENSITIVE_PERSISTENCE_DENIED,
                "form response persistence is disabled",
            )
        artifact = self.store.get_artifact(context.workspace_id, command.artifact_id)
        self.policy.authorize(
            ArtifactPermission.FORM_SUBMIT,
            context,
            artifact_workspace_id=artifact.workspace_id,
            current_data_class=artifact.data_class,
        )
        if artifact.kind is not ArtifactKind.FORM:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID,
                "form submission requires a form artifact",
            )
        stored_revision = self.store.get_revision(
            context.workspace_id,
            artifact.artifact_id,
            command.schema_revision_id,
        )
        content = self._decode_content(artifact.kind, stored_revision.content)
        if not isinstance(content, FormContentV1):
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT,
                "stored form schema has an invalid type",
            )
        validate_form_response(content.json_schema, command.response)
        response_sha256 = hashlib.sha256(
            canonical_json(command.response).encode("utf-8")
        ).hexdigest()
        submission_id = self._stable_id(
            "submission", artifact.artifact_id, command.idempotency_key
        )
        pending = content.behavior.external_continuation == "approval_required"
        created = self.store.create_form_submission(
            submission_id=submission_id,
            workspace_id=context.workspace_id,
            artifact_id=artifact.artifact_id,
            schema_revision_id=command.schema_revision_id,
            principal_id=context.principal_id,
            persistence_policy=command.persistence_policy,
            response_sha256=response_sha256,
            idempotency_key=command.idempotency_key,
            continuation_required=pending,
        )
        approval = None
        if pending:
            gateway = self._continuation_gateway
            if gateway is _DEFAULT_CONTINUATION_GATEWAY:
                gateway = ArtifactFormContinuationGateway(
                    ApprovalStore(state_path("governance", "approvals.sqlite3"))
                )
                self._continuation_gateway = gateway
            if not isinstance(gateway, ArtifactFormContinuationGateway):
                raise ArtifactDomainError(
                    ArtifactErrorCode.ARTIFACT_POLICY_UNAVAILABLE,
                    "form continuation approval is unavailable",
                )
            try:
                approval = gateway.request_approval(
                    context=context,
                    artifact_id=artifact.artifact_id,
                    schema_revision_id=command.schema_revision_id,
                    submission_id=submission_id,
                    response_sha256=response_sha256,
                    idempotency_key=command.idempotency_key,
                )
                self.store.mark_form_continuation_ticketed(
                    submission_id=submission_id,
                    workspace_id=context.workspace_id,
                    approval_id=approval.approval_id,
                    action_hash=approval.action_hash,
                )
            except ArtifactDomainError as exc:
                self.store.mark_form_continuation_failed(
                    submission_id=submission_id,
                    workspace_id=context.workspace_id,
                    error_code=exc.code.value,
                )
                raise
            except Exception as exc:
                self.store.mark_form_continuation_failed(
                    submission_id=submission_id,
                    workspace_id=context.workspace_id,
                    error_code=ArtifactErrorCode.ARTIFACT_POLICY_UNAVAILABLE.value,
                )
                raise ArtifactDomainError(
                    ArtifactErrorCode.ARTIFACT_POLICY_UNAVAILABLE,
                    "form continuation approval is unavailable",
                ) from exc
        return ArtifactFormSubmissionResult(
            submission_id=submission_id,
            artifact_id=artifact.artifact_id,
            schema_revision_id=command.schema_revision_id,
            status="pending_continuation" if pending else "accepted",
            response_sha256=response_sha256,
            continuation_action="require_approval" if pending else "none",
            approval_id=approval.approval_id if approval is not None else None,
            reason_code=(
                "FORM_CONTINUATION_APPROVAL_REQUIRED"
                if pending
                else "FORM_CONTINUATION_NOT_REQUIRED"
            ),
            action_hash=approval.action_hash if approval is not None else None,
            disposition="created" if created else "idempotent_replay",
        )

    @staticmethod
    def _validate_content(
        kind: ArtifactKind,
        payload: object,
        *,
        schema_version: int | None = None,
    ) -> ArtifactContent:
        try:
            return validate_artifact_content(kind, payload, schema_version=schema_version)
        except ArtifactDomainError:
            raise
        except (ValidationError, ValueError, TypeError) as exc:
            code = (
                ArtifactErrorCode.FORM_SCHEMA_UNSAFE
                if kind is ArtifactKind.FORM
                else ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID
            )
            raise ArtifactDomainError(
                code,
                (
                    "form schema is outside the safe supported subset"
                    if kind is ArtifactKind.FORM
                    else "artifact content does not match its versioned schema"
                ),
            ) from exc

    def _decode_content(
        self,
        kind: ArtifactKind,
        payload: bytes,
        *,
        schema_version: int | None = None,
    ) -> ArtifactContent:
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT,
                "stored artifact content is not valid JSON",
            ) from exc
        return self._validate_content(kind, decoded, schema_version=schema_version)

    @staticmethod
    def _request_hash(command: ArtifactModel) -> str:
        return hashlib.sha256(canonical_json(command).encode("utf-8")).hexdigest()

    @staticmethod
    def _stable_id(prefix: str, *parts: str) -> str:
        digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]
        return f"{prefix}-{digest}"

    @staticmethod
    def _decode_cursor(cursor: str | None) -> int:
        if cursor is None:
            return 0
        try:
            offset = int(cursor)
        except ValueError as exc:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID,
                "artifact cursor is invalid",
            ) from exc
        if offset < 0:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID,
                "artifact cursor is invalid",
            )
        return offset

    def _load_operation_replay(
        self,
        workspace_id: str,
        idempotency_key: str,
        operation: str,
        request_hash: str,
    ) -> ArtifactOperationResult | None:
        with self.store._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM artifact_operation_dedup
                WHERE workspace_id = ? AND idempotency_key = ?
                """,
                (workspace_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        if row["operation"] != operation or row["request_sha256"] != request_hash:
            self._raise_conflict("idempotency key payload mismatch")
        result = json.loads(row["result_json"])
        artifact = self.store.get_artifact(workspace_id, result["artifactId"])
        revision = self.store.get_revision(
            workspace_id, artifact.artifact_id, result["revisionId"]
        ).descriptor
        return ArtifactOperationResult(artifact, revision, False, "idempotent_replay")

    def _save_operation_replay(
        self,
        workspace_id: str,
        idempotency_key: str,
        operation: str,
        request_hash: str,
        result: ArtifactOperationResult,
    ) -> None:
        result_json = canonical_json(
            {
                "artifactId": result.artifact.artifact_id,
                "revisionId": result.revision.revision_id,
            }
        )
        with self.store._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO artifact_operation_dedup (
                    workspace_id, idempotency_key, operation, request_sha256,
                    result_json, created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    idempotency_key,
                    operation,
                    request_hash,
                    result_json,
                    datetime.now(UTC).isoformat(),
                ),
            )
            connection.commit()

    @staticmethod
    def _proposal_result(row: sqlite3.Row) -> ArtifactMutationProposalResult:
        return ArtifactMutationProposalResult(
            row["proposal_id"],
            row["artifact_id"],
            row["base_revision_number"],
            row["status"],
            row["content_sha256"],
            row["summary"],
        )

    @staticmethod
    def _raise_conflict(message: str) -> None:
        raise ArtifactDomainError(
            ArtifactErrorCode.ARTIFACT_REVISION_CONFLICT,
            message,
        )
