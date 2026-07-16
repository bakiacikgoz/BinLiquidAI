from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.filesystem import GuardedArtifactFilesystem
from imperaos.artifacts.migrations import (
    DEFAULT_BUSY_TIMEOUT_MS,
    connect_artifact_metadata,
    migrate_artifact_metadata,
)
from imperaos.artifacts.models import (
    ArtifactDescriptor,
    ArtifactMutationType,
    ArtifactRevisionDescriptor,
    canonical_json,
)

WriteDisposition = Literal["created", "no_op", "idempotent_replay"]


@dataclass(frozen=True, slots=True)
class RevisionWriteResult:
    artifact: ArtifactDescriptor
    revision: ArtifactRevisionDescriptor
    created: bool
    disposition: WriteDisposition


@dataclass(frozen=True, slots=True)
class StoredRevision:
    descriptor: ArtifactRevisionDescriptor
    content: bytes


@dataclass(frozen=True, slots=True)
class StorageReconciliationReport:
    pending_journals: int
    recovered_commits: int
    quarantined_files: int
    removed_temp_files: int


def revision_content_relpath(
    workspace_id: str,
    artifact_id: str,
    revision_number: int,
    revision_id: str,
    content_encoding: Literal["utf-8", "json", "binary"],
) -> str:
    if revision_number < 1:
        raise ValueError("revision_number must be positive")
    suffix = {"utf-8": "txt", "json": "json", "binary": "bin"}[content_encoding]
    return (
        f"content/{workspace_id}/{artifact_id}/revisions/"
        f"{revision_number:08d}-{revision_id}.{suffix}"
    )


class ArtifactStore:
    def __init__(
        self,
        root: str | Path,
        *,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        self.filesystem = GuardedArtifactFilesystem(root)
        self.database_path = self.filesystem.metadata_root / "artifacts.sqlite3"
        self.busy_timeout_ms = busy_timeout_ms
        migrate_artifact_metadata(
            self.database_path,
            busy_timeout_ms=self.busy_timeout_ms,
        )

    def create_artifact(
        self,
        artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
        content: bytes,
    ) -> RevisionWriteResult:
        self._validate_payload(artifact, revision, content)
        if (
            revision.revision_number != 1
            or revision.parent_revision_id is not None
            or revision.mutation_type is not ArtifactMutationType.CREATE
            or artifact.current_revision_id != revision.revision_id
            or artifact.current_revision_number != 1
        ):
            self._raise_schema_invalid("invalid initial artifact revision contract")

        replay = self._find_idempotent_result(
            artifact.workspace_id,
            artifact.artifact_id,
            revision.idempotency_key,
            revision.content_sha256,
        )
        if replay is not None:
            return replay
        if self._artifact_exists(artifact.artifact_id):
            self._raise_conflict("artifact already exists", actual_revision=None)

        self._reserve_journal(artifact, revision)
        self._publish_content(revision, content)
        self._commit_create(artifact, revision)
        return RevisionWriteResult(artifact, revision, True, "created")

    def append_revision(
        self,
        updated_artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
        content: bytes,
        *,
        expected_revision_number: int,
    ) -> RevisionWriteResult:
        self._validate_payload(updated_artifact, revision, content)
        current = self.get_artifact(
            updated_artifact.workspace_id,
            updated_artifact.artifact_id,
        )
        replay = self._find_idempotent_result(
            updated_artifact.workspace_id,
            updated_artifact.artifact_id,
            revision.idempotency_key,
            revision.content_sha256,
        )
        if replay is not None:
            return replay
        if current.current_revision_number != expected_revision_number:
            self._raise_conflict(
                "artifact revision is stale",
                actual_revision=current.current_revision_number,
                expected_revision=expected_revision_number,
            )

        current_revision = self._get_revision_descriptor(
            current.workspace_id,
            current.artifact_id,
            current.current_revision_id,
        )
        if current_revision.content_sha256 == revision.content_sha256:
            return RevisionWriteResult(current, current_revision, False, "no_op")

        self._validate_append_contract(
            current,
            updated_artifact,
            revision,
            expected_revision_number,
        )
        self._reserve_journal(updated_artifact, revision)
        self._publish_content(revision, content)
        self._commit_append(updated_artifact, revision, expected_revision_number)
        return RevisionWriteResult(updated_artifact, revision, True, "created")

    def restore_revision(
        self,
        updated_artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
        *,
        source_revision_id: str,
        expected_revision_number: int,
    ) -> RevisionWriteResult:
        if (
            revision.mutation_type is not ArtifactMutationType.RESTORE
            or revision.base_revision_id != source_revision_id
        ):
            self._raise_schema_invalid("restore revision must identify its source revision")
        source = self.get_revision(
            updated_artifact.workspace_id,
            updated_artifact.artifact_id,
            source_revision_id,
        )
        return self.append_revision(
            updated_artifact,
            revision,
            source.content,
            expected_revision_number=expected_revision_number,
        )

    def get_artifact(self, workspace_id: str, artifact_id: str) -> ArtifactDescriptor:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        if row is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_NOT_FOUND,
                "artifact does not exist",
            )
        if row["workspace_id"] != workspace_id:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_WORKSPACE_MISMATCH,
                "artifact belongs to a different workspace",
            )
        return _artifact_from_row(row)

    def get_revision(
        self,
        workspace_id: str,
        artifact_id: str,
        revision_id: str,
    ) -> StoredRevision:
        descriptor = self._get_revision_descriptor(workspace_id, artifact_id, revision_id)
        try:
            content = self.filesystem.read_bytes(
                descriptor.content_relpath,
                expected_sha256=descriptor.content_sha256,
            )
        except ArtifactDomainError as exc:
            if exc.code is ArtifactErrorCode.ARTIFACT_HASH_MISMATCH:
                self._mark_artifact_corrupt(artifact_id, revision_id)
            raise
        return StoredRevision(descriptor, content)

    def list_revisions(
        self,
        workspace_id: str,
        artifact_id: str,
    ) -> tuple[ArtifactRevisionDescriptor, ...]:
        self.get_artifact(workspace_id, artifact_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM artifact_revisions
                WHERE artifact_id = ? ORDER BY revision_number
                """,
                (artifact_id,),
            ).fetchall()
        return tuple(_revision_from_row(row) for row in rows)

    def reconcile_storage(self) -> StorageReconciliationReport:
        with self._connect() as connection:
            pending = connection.execute(
                """
                SELECT * FROM artifact_write_journal
                WHERE state = 'pending' ORDER BY created_at_utc
                """
            ).fetchall()
            referenced = {
                row[0]
                for row in connection.execute(
                    "SELECT content_relpath FROM artifact_revisions"
                ).fetchall()
            }

        recovered_commits = 0
        quarantined_files = 0
        for journal in pending:
            if journal["content_relpath"] in referenced:
                self._set_journal_state(journal["journal_id"], "committed")
                recovered_commits += 1
                continue
            candidate = self.filesystem.resolve_relative(journal["content_relpath"])
            if candidate.exists():
                self.filesystem.quarantine(
                    journal["content_relpath"],
                    reason="pending-write-orphan",
                )
                quarantined_files += 1
            self._set_journal_state(journal["journal_id"], "quarantined")

        for candidate in list(self.filesystem.content_root.rglob("*")):
            if not candidate.is_file():
                continue
            relative_path = candidate.relative_to(self.filesystem.root).as_posix()
            if relative_path not in referenced:
                self.filesystem.quarantine(relative_path, reason="unreferenced-content")
                quarantined_files += 1

        removed_temp_files = 0
        for candidate in list(self.filesystem.tmp_root.rglob("*")):
            if candidate.is_file():
                candidate.unlink()
                removed_temp_files += 1
        return StorageReconciliationReport(
            pending_journals=len(pending),
            recovered_commits=recovered_commits,
            quarantined_files=quarantined_files,
            removed_temp_files=removed_temp_files,
        )

    def _connect(self) -> sqlite3.Connection:
        return connect_artifact_metadata(
            self.database_path,
            busy_timeout_ms=self.busy_timeout_ms,
        )

    def _artifact_exists(self, artifact_id: str) -> bool:
        with self._connect() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM artifacts WHERE artifact_id = ?",
                    (artifact_id,),
                ).fetchone()
                is not None
            )

    def _find_idempotent_result(
        self,
        workspace_id: str,
        artifact_id: str,
        idempotency_key: str,
        content_sha256: str,
    ) -> RevisionWriteResult | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM artifact_revisions
                WHERE artifact_id = ? AND idempotency_key = ?
                """,
                (artifact_id, idempotency_key),
            ).fetchone()
        if row is None:
            return None
        existing = _revision_from_row(row)
        if existing.content_sha256 != content_sha256:
            self._raise_conflict("idempotency key payload mismatch", actual_revision=None)
        artifact = self.get_artifact(workspace_id, artifact_id)
        return RevisionWriteResult(artifact, existing, False, "idempotent_replay")

    def _get_revision_descriptor(
        self,
        workspace_id: str,
        artifact_id: str,
        revision_id: str,
    ) -> ArtifactRevisionDescriptor:
        self.get_artifact(workspace_id, artifact_id)
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM artifact_revisions
                WHERE artifact_id = ? AND revision_id = ?
                """,
                (artifact_id, revision_id),
            ).fetchone()
        if row is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_NOT_FOUND,
                "artifact revision does not exist",
            )
        return _revision_from_row(row)

    def _reserve_journal(
        self,
        artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
    ) -> None:
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO artifact_write_journal (
                        journal_id, workspace_id, artifact_id, revision_id,
                        content_relpath, content_sha256, state, created_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                    """,
                    (
                        revision.revision_id,
                        artifact.workspace_id,
                        artifact.artifact_id,
                        revision.revision_id,
                        revision.content_relpath,
                        revision.content_sha256,
                        datetime.now(UTC).isoformat(),
                    ),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise ArtifactDomainError(
                    ArtifactErrorCode.ARTIFACT_REVISION_CONFLICT,
                    "artifact revision journal already exists",
                ) from exc

    def _publish_content(self, revision: ArtifactRevisionDescriptor, content: bytes) -> None:
        target = self.filesystem.resolve_relative(revision.content_relpath)
        if target.exists():
            self.filesystem.read_bytes(
                revision.content_relpath,
                expected_sha256=revision.content_sha256,
            )
            return
        self.filesystem.atomic_write_bytes(
            revision.content_relpath,
            content,
            expected_sha256=revision.content_sha256,
        )

    def _commit_create(
        self,
        artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
    ) -> None:
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(_ARTIFACT_INSERT_SQL, _artifact_record(artifact))
                connection.execute(_REVISION_INSERT_SQL, _revision_record(revision))
                self._commit_journal(connection, revision.revision_id)
                connection.commit()
            except sqlite3.Error as exc:
                connection.rollback()
                self._raise_storage_failure(exc, "create_commit_failed")

    def _commit_append(
        self,
        artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
        expected_revision_number: int,
    ) -> None:
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(_REVISION_INSERT_SQL, _revision_record(revision))
                record = _artifact_record(artifact)
                record["expected_revision_number"] = expected_revision_number
                cursor = connection.execute(_ARTIFACT_UPDATE_SQL, record)
                if cursor.rowcount != 1:
                    raise ArtifactDomainError(
                        ArtifactErrorCode.ARTIFACT_REVISION_CONFLICT,
                        "artifact revision changed during commit",
                    )
                self._commit_journal(connection, revision.revision_id)
                connection.commit()
            except ArtifactDomainError:
                connection.rollback()
                raise
            except sqlite3.Error as exc:
                connection.rollback()
                self._raise_storage_failure(exc, "revision_commit_failed")

    @staticmethod
    def _commit_journal(connection: sqlite3.Connection, revision_id: str) -> None:
        cursor = connection.execute(
            """
            UPDATE artifact_write_journal
            SET state = 'committed', completed_at_utc = ?
            WHERE revision_id = ? AND state = 'pending'
            """,
            (datetime.now(UTC).isoformat(), revision_id),
        )
        if cursor.rowcount != 1:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT,
                "artifact write journal is not pending",
            )

    def _set_journal_state(self, journal_id: str, state: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE artifact_write_journal
                SET state = ?, completed_at_utc = ? WHERE journal_id = ?
                """,
                (state, datetime.now(UTC).isoformat(), journal_id),
            )
            connection.commit()

    def _mark_artifact_corrupt(self, artifact_id: str, revision_id: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE artifacts
                SET status = 'corrupt', updated_at_utc = ?, etag = ?
                WHERE artifact_id = ?
                """,
                (
                    datetime.now(UTC).isoformat(),
                    f"corrupt-{revision_id}",
                    artifact_id,
                ),
            )
            connection.commit()

    @staticmethod
    def _validate_payload(
        artifact: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
        content: bytes,
    ) -> None:
        digest = hashlib.sha256(content).hexdigest()
        expected_path = revision_content_relpath(
            artifact.workspace_id,
            artifact.artifact_id,
            revision.revision_number,
            revision.revision_id,
            revision.content_encoding,
        )
        if (
            revision.artifact_id != artifact.artifact_id
            or revision.content_relpath != expected_path
        ):
            ArtifactStore._raise_schema_invalid("revision identity or content path is invalid")
        if revision.content_sha256 != digest or revision.content_size_bytes != len(content):
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_HASH_MISMATCH,
                "revision payload hash or size does not match its descriptor",
            )

    @staticmethod
    def _validate_append_contract(
        current: ArtifactDescriptor,
        updated: ArtifactDescriptor,
        revision: ArtifactRevisionDescriptor,
        expected_revision_number: int,
    ) -> None:
        if (
            updated.workspace_id != current.workspace_id
            or updated.artifact_id != current.artifact_id
            or updated.created_at_utc != current.created_at_utc
            or updated.created_by_id != current.created_by_id
            or revision.revision_number != expected_revision_number + 1
            or revision.parent_revision_id != current.current_revision_id
            or updated.current_revision_id != revision.revision_id
            or updated.current_revision_number != revision.revision_number
        ):
            ArtifactStore._raise_schema_invalid("revision update contract is inconsistent")

    @staticmethod
    def _raise_schema_invalid(message: str) -> None:
        raise ArtifactDomainError(ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID, message)

    @staticmethod
    def _raise_conflict(
        message: str,
        *,
        actual_revision: int | None,
        expected_revision: int | None = None,
    ) -> None:
        raise ArtifactDomainError(
            ArtifactErrorCode.ARTIFACT_REVISION_CONFLICT,
            message,
            details={
                "actualRevision": actual_revision,
                "expectedRevision": expected_revision,
            },
        )

    @staticmethod
    def _raise_storage_failure(exc: sqlite3.Error, classification: str) -> None:
        if isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower():
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_STORAGE_LOCKED,
                "artifact metadata is temporarily locked",
                retryable=True,
                details={"classification": "storage_locked"},
            ) from exc
        raise ArtifactDomainError(
            ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT,
            "artifact metadata commit failed",
            details={"classification": classification},
        ) from exc


_ARTIFACT_INSERT_SQL = """
INSERT INTO artifacts (
    artifact_id, workspace_id, kind, title, status, schema_version, data_class,
    current_revision_id, current_revision_number, source_session_id, source_turn_id,
    created_by_type, created_by_id, updated_by_id, created_at_utc, updated_at_utc,
    archived_at_utc, etag, metadata_json
) VALUES (
    :artifact_id, :workspace_id, :kind, :title, :status, :schema_version, :data_class,
    :current_revision_id, :current_revision_number, :source_session_id, :source_turn_id,
    :created_by_type, :created_by_id, :updated_by_id, :created_at_utc, :updated_at_utc,
    :archived_at_utc, :etag, :metadata_json
)
"""

_ARTIFACT_UPDATE_SQL = """
UPDATE artifacts SET
    kind = :kind,
    title = :title,
    status = :status,
    schema_version = :schema_version,
    data_class = :data_class,
    current_revision_id = :current_revision_id,
    current_revision_number = :current_revision_number,
    source_session_id = :source_session_id,
    source_turn_id = :source_turn_id,
    updated_by_id = :updated_by_id,
    updated_at_utc = :updated_at_utc,
    archived_at_utc = :archived_at_utc,
    etag = :etag,
    metadata_json = :metadata_json
WHERE artifact_id = :artifact_id
  AND workspace_id = :workspace_id
  AND current_revision_number = :expected_revision_number
"""

_REVISION_INSERT_SQL = """
INSERT INTO artifact_revisions (
    revision_id, artifact_id, parent_revision_id, base_revision_id, revision_number,
    mutation_type, content_relpath, content_sha256, content_size_bytes, content_encoding,
    change_summary, author_type, author_id, idempotency_key, created_at_utc
) VALUES (
    :revision_id, :artifact_id, :parent_revision_id, :base_revision_id, :revision_number,
    :mutation_type, :content_relpath, :content_sha256, :content_size_bytes, :content_encoding,
    :change_summary, :author_type, :author_id, :idempotency_key, :created_at_utc
)
"""


def _artifact_record(artifact: ArtifactDescriptor) -> dict[str, object]:
    return {
        "artifact_id": artifact.artifact_id,
        "workspace_id": artifact.workspace_id,
        "kind": artifact.kind.value,
        "title": artifact.title,
        "status": artifact.status.value,
        "schema_version": artifact.schema_version,
        "data_class": artifact.data_class.value,
        "current_revision_id": artifact.current_revision_id,
        "current_revision_number": artifact.current_revision_number,
        "source_session_id": artifact.source_session_id,
        "source_turn_id": artifact.source_turn_id,
        "created_by_type": artifact.created_by_type.value,
        "created_by_id": artifact.created_by_id,
        "updated_by_id": artifact.updated_by_id,
        "created_at_utc": artifact.created_at_utc.isoformat(),
        "updated_at_utc": artifact.updated_at_utc.isoformat(),
        "archived_at_utc": artifact.archived_at_utc.isoformat()
        if artifact.archived_at_utc
        else None,
        "etag": artifact.etag,
        "metadata_json": canonical_json(artifact.metadata),
    }


def _revision_record(revision: ArtifactRevisionDescriptor) -> dict[str, object]:
    return {
        "revision_id": revision.revision_id,
        "artifact_id": revision.artifact_id,
        "parent_revision_id": revision.parent_revision_id,
        "base_revision_id": revision.base_revision_id,
        "revision_number": revision.revision_number,
        "mutation_type": revision.mutation_type.value,
        "content_relpath": revision.content_relpath,
        "content_sha256": revision.content_sha256,
        "content_size_bytes": revision.content_size_bytes,
        "content_encoding": revision.content_encoding,
        "change_summary": revision.change_summary,
        "author_type": revision.author_type.value,
        "author_id": revision.author_id,
        "idempotency_key": revision.idempotency_key,
        "created_at_utc": revision.created_at_utc.isoformat(),
    }


def _artifact_from_row(row: sqlite3.Row) -> ArtifactDescriptor:
    return ArtifactDescriptor(
        artifact_id=row["artifact_id"],
        workspace_id=row["workspace_id"],
        kind=row["kind"],
        title=row["title"],
        status=row["status"],
        schema_version=row["schema_version"],
        data_class=row["data_class"],
        current_revision_id=row["current_revision_id"],
        current_revision_number=row["current_revision_number"],
        source_session_id=row["source_session_id"],
        source_turn_id=row["source_turn_id"],
        created_by_type=row["created_by_type"],
        created_by_id=row["created_by_id"],
        updated_by_id=row["updated_by_id"],
        created_at_utc=datetime.fromisoformat(row["created_at_utc"]),
        updated_at_utc=datetime.fromisoformat(row["updated_at_utc"]),
        archived_at_utc=datetime.fromisoformat(row["archived_at_utc"])
        if row["archived_at_utc"]
        else None,
        etag=row["etag"],
        metadata=json.loads(row["metadata_json"]),
    )


def _revision_from_row(row: sqlite3.Row) -> ArtifactRevisionDescriptor:
    return ArtifactRevisionDescriptor(
        revision_id=row["revision_id"],
        artifact_id=row["artifact_id"],
        parent_revision_id=row["parent_revision_id"],
        base_revision_id=row["base_revision_id"],
        revision_number=row["revision_number"],
        mutation_type=row["mutation_type"],
        content_relpath=row["content_relpath"],
        content_sha256=row["content_sha256"],
        content_size_bytes=row["content_size_bytes"],
        content_encoding=row["content_encoding"],
        change_summary=row["change_summary"],
        author_type=row["author_type"],
        author_id=row["author_id"],
        idempotency_key=row["idempotency_key"],
        created_at_utc=datetime.fromisoformat(row["created_at_utc"]),
    )
