from __future__ import annotations

import fnmatch
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from binliquid.memory.models import StrictModel

ArtifactSourceType = Literal[
    "local_current_host",
    "github_actions",
    "self_hosted_runner",
    "manual_bundle",
]
ArtifactAuthMode = Literal["auto", "gh_cli", "token_env", "none"]
HarvestStatus = Literal["pass", "conditional", "blocked", "fail"]

SAFE_PATTERN_RE = re.compile(r"^[A-Za-z0-9._*?{}()[\]-]+$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def current_git_head() -> str:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        shell=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def current_git_branch() -> str:
    import subprocess

    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        shell=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def validate_safe_artifact_pattern(pattern: str) -> str:
    if (
        not pattern
        or ".." in pattern
        or "/" in pattern
        or "\\" in pattern
        or not SAFE_PATTERN_RE.match(pattern)
    ):
        raise ValueError("INVALID_ARTIFACT_PATTERN")
    return pattern


def artifact_name_matches(name: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(name, pattern)


def normalize_report_path(path: Path, root: Path | None = None) -> str:
    root = root or Path.cwd()
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


class RemoteArtifactSource(StrictModel):
    source_id: str = Field(alias="sourceId")
    source_type: ArtifactSourceType = Field(alias="sourceType")
    repo: str | None = None
    workflow: str | None = None
    branch: str | None = None
    head_sha: str | None = Field(default=None, alias="headSha")
    artifact_pattern: str = Field(
        default="local-product-evidence-*",
        alias="artifactPattern",
    )
    auth_mode: ArtifactAuthMode = Field(default="auto", alias="authMode")

    @field_validator("source_id")
    @classmethod
    def _source_id_safe(cls, value: str) -> str:
        if not re.match(r"^[A-Za-z0-9_.-]+$", value):
            raise ValueError("INVALID_SOURCE_ID")
        return value

    @field_validator("repo")
    @classmethod
    def _repo_safe(cls, value: str | None) -> str | None:
        if value is not None and not REPO_RE.match(value):
            raise ValueError("INVALID_REPO_SLUG")
        return value

    @field_validator("head_sha")
    @classmethod
    def _head_sha_safe(cls, value: str | None) -> str | None:
        if value is not None and not SHA_RE.match(value):
            raise ValueError("INVALID_HEAD_SHA")
        return value

    @field_validator("artifact_pattern")
    @classmethod
    def _pattern_safe(cls, value: str) -> str:
        return validate_safe_artifact_pattern(value)


class RemoteArtifact(StrictModel):
    artifact_id: str = Field(alias="artifactId")
    source_id: str = Field(alias="sourceId")
    source_type: ArtifactSourceType = Field(alias="sourceType")
    name: str
    target: str | None = None
    head_sha: str | None = Field(default=None, alias="headSha")
    size_in_bytes: int | None = Field(default=None, alias="sizeInBytes")
    expired: bool = False
    archive_download_url_redacted: str | None = Field(
        default=None,
        alias="archiveDownloadUrlRedacted",
    )
    metadata_redacted: dict[str, str | int | bool | None] = Field(
        default_factory=dict,
        alias="metadataRedacted",
    )


class DownloadedArtifact(StrictModel):
    artifact_id: str = Field(alias="artifactId")
    source_id: str = Field(alias="sourceId")
    target: str | None = None
    head_sha: str | None = Field(default=None, alias="headSha")
    downloaded_path: str = Field(alias="downloadedPath")
    sha256: str
    downloaded_at_utc: str = Field(alias="downloadedAtUtc")
    metadata_redacted: dict[str, str | int | bool | None] = Field(
        default_factory=dict,
        alias="metadataRedacted",
    )


class ArtifactDiscoveryRequest(StrictModel):
    source: RemoteArtifactSource
    branch: str
    head_sha: str = Field(alias="headSha")
    workflow: str | None = None
    limit: int = 20


class ArtifactDiscoveryReport(StrictModel):
    schema_version: Literal["local_product_artifact_discovery/v1"] = Field(
        default="local_product_artifact_discovery/v1",
        alias="schemaVersion",
    )
    status: HarvestStatus
    source: RemoteArtifactSource
    branch: str
    head_sha: str = Field(alias="headSha")
    artifacts: list[RemoteArtifact] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")
    warnings: list[str] = Field(default_factory=list)
    generated_at_utc: str = Field(default_factory=utc_now, alias="generatedAtUtc")


class HarvestTargetResult(StrictModel):
    target: str
    status: Literal[
        "evidenced",
        "not_evidenced",
        "stale",
        "blocked",
        "downloaded",
        "skipped",
    ]
    source_id: str | None = Field(default=None, alias="sourceId")
    artifact_id: str | None = Field(default=None, alias="artifactId")
    bundle_sha256: str | None = Field(default=None, alias="bundleSha256")
    evidence_id: str | None = Field(default=None, alias="evidenceId")
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")


class PlatformEvidenceHarvestReport(StrictModel):
    schema_version: Literal["local_product_harvest/v1"] = Field(
        default="local_product_harvest/v1",
        alias="schemaVersion",
    )
    status: HarvestStatus
    head_sha: str = Field(alias="headSha")
    branch: str
    sources: list[RemoteArtifactSource] = Field(default_factory=list)
    artifacts_discovered: int = Field(default=0, alias="artifactsDiscovered")
    artifacts_downloaded: int = Field(default=0, alias="artifactsDownloaded")
    artifacts_imported: int = Field(default=0, alias="artifactsImported")
    target_results: list[HarvestTargetResult] = Field(
        default_factory=list,
        alias="targetResults",
    )
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reconciliation: dict[str, object] | None = None
    output_root: str | None = Field(default=None, alias="outputRoot")
    generated_at_utc: str = Field(default_factory=utc_now, alias="generatedAtUtc")

