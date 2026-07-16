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
    CreateArtifactCommand,
    DuplicateArtifactCommand,
    GetArtifactQuery,
    ListArtifactsQuery,
    MutateArtifactCommand,
    ProposeArtifactMutationCommand,
    RestoreArtifactCommand,
)
from imperaos.artifacts.content import ArtifactContent, validate_artifact_content
from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.evidence import (
    ArtifactEvidenceRecorder,
    record_artifact_evidence,
)
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
    ArtifactHistoryResult,
    ArtifactListResult,
    ArtifactMutationProposalResult,
    ArtifactOperationResult,
    ArtifactReadResult,
)
from imperaos.artifacts.store import ArtifactStore, revision_content_relpath


class ArtifactService:
    """Policy-enforced application service for governed artifact operations."""

    def __init__(
        self,
        root: str | Path,
        *,
        policy: ArtifactPolicyGateway | None = None,
        evidence: ArtifactEvidenceRecorder | None = None,
    ) -> None:
        self.store = ArtifactStore(root)
        self.policy = policy or ArtifactPolicyGateway()
        self.evidence = evidence or ArtifactEvidenceRecorder(self.store.database_path)

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
            schema_version=1,
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
        result = self.store.create_artifact(artifact, revision, payload)
        operation = ArtifactOperationResult(
            artifact=result.artifact,
            revision=result.revision,
            created=result.created,
            disposition=result.disposition,
        )
        self._save_operation_replay(
            context.workspace_id,
            command.idempotency_key,
            "create",
            request_hash,
            operation,
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
        content = self._decode_content(artifact.kind, revision.content)
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
        if permission is ArtifactPermission.AI_APPLY and command.proposal_id is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_PERMISSION_DENIED,
                "assistant mutations require an approved proposal",
            )

        content = self._validate_content(current.kind, command.content)
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
        )
        return ArtifactOperationResult(
            stored.artifact,
            stored.revision,
            stored.created,
            stored.disposition,
        )

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
        content = self._validate_content(artifact.kind, command.content)
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
        source = self.store.get_revision(
            context.workspace_id, command.artifact_id, command.source_revision_id
        )
        content = self._decode_content(current.kind, source.content)
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
        )
        return ArtifactOperationResult(
            stored.artifact,
            stored.revision,
            stored.created,
            stored.disposition,
        )

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
        loaded = self.get(GetArtifactQuery(artifact_id=source.artifact_id), context)
        return self.create(
            CreateArtifactCommand(
                artifact_id=command.artifact_id,
                kind=source.kind,
                title=command.title,
                data_class=source.data_class,
                content=loaded.content.model_dump(mode="json", by_alias=True),
                idempotency_key=command.idempotency_key,
                source_session_id=source.source_session_id,
                source_turn_id=source.source_turn_id,
                metadata=source.metadata,
            ),
            context,
        )

    @staticmethod
    def _validate_content(kind: ArtifactKind, payload: object) -> ArtifactContent:
        try:
            return validate_artifact_content(kind, payload)
        except ArtifactDomainError:
            raise
        except (ValidationError, ValueError, TypeError) as exc:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID,
                "artifact content does not match its versioned schema",
            ) from exc

    def _decode_content(self, kind: ArtifactKind, payload: bytes) -> ArtifactContent:
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT,
                "stored artifact content is not valid JSON",
            ) from exc
        return self._validate_content(kind, decoded)

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
