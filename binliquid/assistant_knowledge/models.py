from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from binliquid.memory.models import StrictModel


class KnowledgeDomain(StrEnum):
    CONTROL_PLANE = "control_plane"
    ASSISTANT = "assistant"
    MEMORY = "memory"
    PROVIDER = "provider"
    COMPUTER_USE = "computer_use"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    UI = "ui"


class KnowledgeSourceKind(StrEnum):
    MARKDOWN = "markdown"
    JSON_SCHEMA = "json_schema"
    YAML_EXAMPLE = "yaml_example"
    MAKEFILE = "makefile"
    TS_SOURCE = "ts_source"
    PY_CLI = "py_cli"


class KnowledgeIntent(StrEnum):
    PLATFORM_USAGE = "platform_usage"
    AGENT_TASK = "agent_task"
    APPROVAL = "approval"
    RUN_EVIDENCE = "run_evidence"
    PROVIDER = "provider"
    MEMORY = "memory"
    COMPUTER_USE = "computer_use"
    DEPLOYMENT = "deployment"
    UNKNOWN = "unknown"


class KnowledgeSource(StrictModel):
    source_id: str = Field(alias="sourceId")
    path: str
    kind: KnowledgeSourceKind
    domain: KnowledgeDomain
    required: bool = False
    hash_sha256: str = Field(alias="hashSha256")
    last_modified: str | None = Field(default=None, alias="lastModified")

    @field_validator("path")
    @classmethod
    def _safe_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("knowledge source path must be repo-relative")
        return normalized


class KnowledgeChunk(StrictModel):
    chunk_id: str = Field(alias="chunkId")
    source_id: str = Field(alias="sourceId")
    path: str
    heading: str = Field(default="", max_length=240)
    body: str = Field(max_length=6000)
    aliases: tuple[str, ...] = ()
    domain: KnowledgeDomain
    commands: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = Field(default=(), alias="reasonCodes")
    content_hash: str = Field(alias="contentHash")


class KnowledgeHit(StrictModel):
    chunk_id: str = Field(alias="chunkId")
    path: str
    heading: str = ""
    snippet: str = Field(max_length=1200)
    score: float = Field(ge=0.0, le=1.0)
    matched_terms: tuple[str, ...] = Field(default=(), alias="matchedTerms")
    commands: tuple[str, ...] = ()
    source_hash: str = Field(alias="sourceHash")


class KnowledgeSearchRequest(StrictModel):
    query: str = Field(min_length=1, max_length=8000)
    profile: str = "enterprise"
    max_hits: int = Field(default=8, alias="maxHits", ge=1, le=20)
    max_context_chars: int = Field(default=8000, alias="maxContextChars", ge=256, le=12000)
    intent_hint: KnowledgeIntent | None = Field(default=None, alias="intentHint")


class KnowledgeSearchResult(StrictModel):
    schema_version: Literal["assistant.system-knowledge-search/v1"] = Field(
        default="assistant.system-knowledge-search/v1",
        alias="schemaVersion",
    )
    status: Literal["ready", "no_hits", "stale", "blocked"]
    intent: KnowledgeIntent
    query_hash: str = Field(alias="queryHash")
    normalized_query: str = Field(alias="normalizedQuery")
    hits: tuple[KnowledgeHit, ...] = ()
    blocking_reasons: tuple[str, ...] = Field(default=(), alias="blockingReasons")
    generated_at_utc: str = Field(alias="generatedAtUtc")


class AssistantSystemKnowledgeContext(StrictModel):
    status: Literal["available", "unavailable", "stale", "blocked"]
    identity_brief: str = Field(alias="identityBrief", max_length=1500)
    answer_rules: tuple[str, ...] = Field(default=(), alias="answerRules")
    sources: tuple[KnowledgeHit, ...] = ()
    context_text: str = Field(default="", alias="contextText", max_length=12000)
    omitted_sources: tuple[str, ...] = Field(default=(), alias="omittedSources")
    blocking_reasons: tuple[str, ...] = Field(default=(), alias="blockingReasons")


class SystemKnowledgeManifest(StrictModel):
    schema_version: Literal["assistant.system-knowledge-manifest/v1"] = Field(
        default="assistant.system-knowledge-manifest/v1",
        alias="schemaVersion",
    )
    profile: str
    status: Literal["ready", "blocked"]
    repo_sha: str = Field(alias="repoSha")
    source_count: int = Field(alias="sourceCount", ge=0)
    chunk_count: int = Field(alias="chunkCount", ge=0)
    manifest_hash: str = Field(alias="manifestHash")
    blocking_reasons: tuple[str, ...] = Field(default=(), alias="blockingReasons")
    generated_at_utc: str = Field(alias="generatedAtUtc")
    sources: tuple[KnowledgeSource, ...] = ()


class SystemKnowledgeDoctor(StrictModel):
    schema_version: Literal["assistant.system-knowledge-doctor/v1"] = Field(
        default="assistant.system-knowledge-doctor/v1",
        alias="schemaVersion",
    )
    profile: str
    status: Literal["ready", "missing", "stale", "blocked"]
    manifest_exists: bool = Field(alias="manifestExists")
    stale: bool
    required_source_missing_count: int = Field(alias="requiredSourceMissingCount")
    source_count: int = Field(alias="sourceCount", ge=0)
    chunk_count: int = Field(alias="chunkCount", ge=0)
    manifest_hash: str | None = Field(default=None, alias="manifestHash")
    blocking_reasons: tuple[str, ...] = Field(default=(), alias="blockingReasons")
    generated_at_utc: str = Field(alias="generatedAtUtc")


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
