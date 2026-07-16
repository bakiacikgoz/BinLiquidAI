from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.filesystem import GuardedArtifactFilesystem
from imperaos.artifacts.migrations import (
    DEFAULT_BUSY_TIMEOUT_MS,
    connect_artifact_metadata,
    migrate_artifact_metadata,
)
from imperaos.artifacts.models import ArtifactAssetDescriptor, ArtifactDataClass

DEFAULT_MAX_ASSET_BYTES = 20 * 1024 * 1024
DEFAULT_WORKSPACE_ASSET_QUOTA_BYTES = 2 * 1024 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class AssetImportResult:
    descriptor: ArtifactAssetDescriptor
    deduplicated: bool


class ArtifactAssetStore:
    def __init__(
        self,
        root: str | Path,
        *,
        max_asset_bytes: int = DEFAULT_MAX_ASSET_BYTES,
        workspace_quota_bytes: int = DEFAULT_WORKSPACE_ASSET_QUOTA_BYTES,
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        if max_asset_bytes < 1 or workspace_quota_bytes < 1:
            raise ValueError("asset limits must be positive")
        self.filesystem = GuardedArtifactFilesystem(root)
        self.database_path = self.filesystem.metadata_root / "artifacts.sqlite3"
        self.max_asset_bytes = min(max_asset_bytes, DEFAULT_MAX_ASSET_BYTES)
        self.workspace_quota_bytes = workspace_quota_bytes
        self.busy_timeout_ms = busy_timeout_ms
        migrate_artifact_metadata(
            self.database_path,
            busy_timeout_ms=self.busy_timeout_ms,
        )

    def import_bytes(
        self,
        workspace_id: str,
        payload: bytes,
        *,
        declared_media_type: str,
        data_class: ArtifactDataClass,
        created_by_id: str,
        original_name: str | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> AssetImportResult:
        if not payload:
            self._raise_type_unsupported("empty_payload")
        if len(payload) > self.max_asset_bytes:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_CONTENT_TOO_LARGE,
                "asset exceeds the per-file size limit",
                details={
                    "limitBytes": self.max_asset_bytes,
                    "actualBytes": len(payload),
                },
            )

        detected_media_type = _detect_media_type(payload)
        digest = hashlib.sha256(payload).hexdigest()
        if detected_media_type == "image/svg+xml":
            quarantine_relpath = self._quarantine_svg(payload, digest)
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_ASSET_UNSAFE,
                "SVG assets require a separate sanitizer and remain quarantined",
                details={
                    "classification": "svg_quarantined",
                    "quarantineRelpath": quarantine_relpath,
                },
            )
        if detected_media_type is None:
            self._raise_type_unsupported("magic_bytes_unknown")
        if declared_media_type != detected_media_type:
            self._raise_type_unsupported("declared_mime_mismatch")

        existing = self._find_by_hash(workspace_id, digest)
        if existing is not None:
            self.filesystem.read_bytes(
                existing.relative_path,
                expected_sha256=existing.sha256,
            )
            return AssetImportResult(existing, True)

        current_usage = self.workspace_usage_bytes(workspace_id)
        if current_usage + len(payload) > self.workspace_quota_bytes:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_QUOTA_EXCEEDED,
                "workspace asset quota would be exceeded",
                details={
                    "limitBytes": self.workspace_quota_bytes,
                    "currentBytes": current_usage,
                    "requestedBytes": len(payload),
                },
            )

        relative_path = f"assets/{workspace_id}/sha256/{digest[:2]}/{digest}"
        asset_id = "asset-" + hashlib.sha256(f"{workspace_id}:{digest}".encode()).hexdigest()[:32]
        try:
            descriptor = ArtifactAssetDescriptor(
                asset_id=asset_id,
                workspace_id=workspace_id,
                sha256=digest,
                media_type=detected_media_type,
                size_bytes=len(payload),
                relative_path=relative_path,
                width=width,
                height=height,
                original_name=original_name,
                data_class=data_class,
                created_by_id=created_by_id,
                created_at_utc=datetime.now(UTC),
            )
        except ValidationError as exc:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_SCHEMA_INVALID,
                "asset metadata is invalid",
            ) from exc

        target = self.filesystem.resolve_relative(relative_path)
        if target.exists():
            self.filesystem.read_bytes(relative_path, expected_sha256=digest)
        else:
            self.filesystem.atomic_write_bytes(
                relative_path,
                payload,
                expected_sha256=digest,
            )
        try:
            return self._insert_or_get_deduplicated(descriptor)
        except ArtifactDomainError as exc:
            if (
                exc.code is ArtifactErrorCode.ARTIFACT_QUOTA_EXCEEDED
                and self._find_by_hash(workspace_id, digest) is None
                and target.exists()
            ):
                self.filesystem.quarantine(relative_path, reason="asset-quota-rejected")
            raise

    def import_remote_url(self, workspace_id: str, url: str) -> None:
        del workspace_id, url
        raise ArtifactDomainError(
            ArtifactErrorCode.ARTIFACT_ASSET_UNSAFE,
            "remote asset fetch is disabled",
            details={"classification": "remote_fetch_denied"},
        )

    def get_descriptor(self, workspace_id: str, asset_id: str) -> ArtifactAssetDescriptor:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifact_assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
        if row is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_NOT_FOUND,
                "artifact asset does not exist",
            )
        if row["workspace_id"] != workspace_id:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_WORKSPACE_MISMATCH,
                "artifact asset belongs to a different workspace",
            )
        return _asset_from_row(row)

    def get_bytes(self, workspace_id: str, asset_id: str) -> bytes:
        descriptor = self.get_descriptor(workspace_id, asset_id)
        return self.filesystem.read_bytes(
            descriptor.relative_path,
            expected_sha256=descriptor.sha256,
        )

    def workspace_usage_bytes(self, workspace_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(size_bytes), 0)
                FROM artifact_assets WHERE workspace_id = ?
                """,
                (workspace_id,),
            ).fetchone()
        return int(row[0])

    def _find_by_hash(
        self,
        workspace_id: str,
        digest: str,
    ) -> ArtifactAssetDescriptor | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM artifact_assets
                WHERE workspace_id = ? AND sha256 = ?
                """,
                (workspace_id, digest),
            ).fetchone()
        return None if row is None else _asset_from_row(row)

    def _insert_or_get_deduplicated(
        self,
        descriptor: ArtifactAssetDescriptor,
    ) -> AssetImportResult:
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                existing_row = connection.execute(
                    """
                    SELECT * FROM artifact_assets
                    WHERE workspace_id = ? AND sha256 = ?
                    """,
                    (descriptor.workspace_id, descriptor.sha256),
                ).fetchone()
                if existing_row is not None:
                    connection.rollback()
                    return AssetImportResult(_asset_from_row(existing_row), True)
                usage_row = connection.execute(
                    """
                    SELECT COALESCE(SUM(size_bytes), 0)
                    FROM artifact_assets WHERE workspace_id = ?
                    """,
                    (descriptor.workspace_id,),
                ).fetchone()
                current_usage = int(usage_row[0])
                if current_usage + descriptor.size_bytes > self.workspace_quota_bytes:
                    raise ArtifactDomainError(
                        ArtifactErrorCode.ARTIFACT_QUOTA_EXCEEDED,
                        "workspace asset quota would be exceeded",
                        details={
                            "limitBytes": self.workspace_quota_bytes,
                            "currentBytes": current_usage,
                            "requestedBytes": descriptor.size_bytes,
                        },
                    )
                connection.execute(
                    """
                    INSERT INTO artifact_assets (
                        asset_id, workspace_id, sha256, media_type, size_bytes,
                        relative_path, width, height, original_name, data_class,
                        created_by_id, created_at_utc
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        descriptor.asset_id,
                        descriptor.workspace_id,
                        descriptor.sha256,
                        descriptor.media_type,
                        descriptor.size_bytes,
                        descriptor.relative_path,
                        descriptor.width,
                        descriptor.height,
                        descriptor.original_name,
                        descriptor.data_class.value,
                        descriptor.created_by_id,
                        descriptor.created_at_utc.isoformat(),
                    ),
                )
                connection.commit()
                return AssetImportResult(descriptor, False)
            except ArtifactDomainError:
                connection.rollback()
                raise
            except sqlite3.IntegrityError:
                connection.rollback()
        existing = self._find_by_hash(descriptor.workspace_id, descriptor.sha256)
        if existing is None:
            raise ArtifactDomainError(
                ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT,
                "asset metadata could not be committed",
            )
        return AssetImportResult(existing, True)

    def _quarantine_svg(self, payload: bytes, digest: str) -> str:
        relative_path = f"quarantine/unsafe-svg/{digest}.svg"
        target = self.filesystem.resolve_relative(relative_path)
        if target.exists():
            self.filesystem.read_bytes(relative_path, expected_sha256=digest)
        else:
            self.filesystem.atomic_write_bytes(
                relative_path,
                payload,
                expected_sha256=digest,
            )
        return relative_path

    def _connect(self) -> sqlite3.Connection:
        return connect_artifact_metadata(
            self.database_path,
            busy_timeout_ms=self.busy_timeout_ms,
        )

    @staticmethod
    def _raise_type_unsupported(classification: str) -> None:
        raise ArtifactDomainError(
            ArtifactErrorCode.ARTIFACT_ASSET_TYPE_UNSUPPORTED,
            "asset media type is not supported or does not match its content",
            details={"classification": classification},
        )


def _detect_media_type(payload: bytes) -> str | None:
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(payload) >= 12 and payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
        return "image/webp"
    normalized = payload[:4096].lstrip(b"\xef\xbb\xbf\x00\t\r\n ").lower()
    if normalized.startswith(b"<svg") or (
        normalized.startswith(b"<?xml") and b"<svg" in normalized
    ):
        return "image/svg+xml"
    return None


def _asset_from_row(row: sqlite3.Row) -> ArtifactAssetDescriptor:
    return ArtifactAssetDescriptor(
        asset_id=row["asset_id"],
        workspace_id=row["workspace_id"],
        sha256=row["sha256"],
        media_type=row["media_type"],
        size_bytes=row["size_bytes"],
        relative_path=row["relative_path"],
        width=row["width"],
        height=row["height"],
        original_name=row["original_name"],
        data_class=row["data_class"],
        created_by_id=row["created_by_id"],
        created_at_utc=datetime.fromisoformat(row["created_at_utc"]),
    )
