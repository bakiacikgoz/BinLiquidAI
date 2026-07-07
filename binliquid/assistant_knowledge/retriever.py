from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from binliquid.assistant_knowledge.index import CHUNKS_NAME, DEFAULT_INDEX_ROOT, load_manifest
from binliquid.assistant_knowledge.models import (
    KnowledgeChunk,
    KnowledgeHit,
    KnowledgeIntent,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    sha256_text,
    utc_now_iso,
)

ALIASES = (
    ("ageisos", "aegisos"),
    ("aegis os", "aegisos"),
    ("aegis", "aegisos"),
    ("görev", "gorev"),
    ("ajan", "agent"),
    ("çalıştırma", "run"),
    ("calistirma", "run"),
)

INTENT_TERMS: dict[KnowledgeIntent, tuple[str, ...]] = {
    KnowledgeIntent.AGENT_TASK: ("agent", "gorev", "task", "gateway", "submit"),
    KnowledgeIntent.APPROVAL: ("approval", "onay", "policy", "approve"),
    KnowledgeIntent.RUN_EVIDENCE: ("run", "evidence", "blocked", "artifact", "replay"),
    KnowledgeIntent.PROVIDER: ("provider", "model", "openai", "anthropic", "ollama"),
    KnowledgeIntent.MEMORY: ("memory", "hafiza", "scope"),
    KnowledgeIntent.COMPUTER_USE: ("computer", "computer-use", "bilgisayar", "vision"),
    KnowledgeIntent.DEPLOYMENT: ("deploy", "install", "setup", "first-run", "mac"),
    KnowledgeIntent.PLATFORM_USAGE: ("aegisos", "binliquid", "nereden", "biliyorsun", "platform"),
}


def normalize_query(value: str) -> str:
    lowered = value.strip().lower().replace("ı", "i")
    simplified = "".join(
        char for char in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(char)
    )
    normalized = re.sub(r"[^a-z0-9_.:/-]+", " ", simplified)
    for source, target in ALIASES:
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def classify_intent(normalized_query: str) -> KnowledgeIntent:
    scores = {
        intent: sum(1 for term in terms if term in normalized_query)
        for intent, terms in INTENT_TERMS.items()
    }
    best = max(scores.items(), key=lambda item: item[1])
    return best[0] if best[1] > 0 else KnowledgeIntent.UNKNOWN


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9_-]+", normalize_query(value)) if len(token) > 1}


def _load_chunks(index_root: Path) -> tuple[KnowledgeChunk, ...]:
    path = index_root / CHUNKS_NAME
    if not path.exists():
        return ()
    chunks: list[KnowledgeChunk] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        chunks.append(KnowledgeChunk.model_validate_json(line))
    return tuple(chunks)


def _score_chunk(
    chunk: KnowledgeChunk,
    query: str,
    intent: KnowledgeIntent | str,
) -> tuple[float, tuple[str, ...]]:
    query_tokens = _tokens(query)
    heading_tokens = _tokens(chunk.heading)
    body_tokens = _tokens(chunk.body)
    path_tokens = _tokens(chunk.path)
    alias_tokens = (
        set().union(*(_tokens(alias) for alias in chunk.aliases)) if chunk.aliases else set()
    )
    command_tokens = (
        set().union(*(_tokens(command) for command in chunk.commands))
        if chunk.commands
        else set()
    )
    matched = tuple(
        sorted(query_tokens.intersection(heading_tokens | body_tokens | path_tokens | alias_tokens))
    )
    heading = 0.35 if query_tokens.intersection(heading_tokens) else 0.0
    alias = 0.25 if query_tokens.intersection(alias_tokens) else 0.0
    command_path = 0.20 if query_tokens.intersection(command_tokens | path_tokens) else 0.0
    overlap = min(
        0.15,
        0.15 * (len(query_tokens.intersection(body_tokens)) / max(1, len(query_tokens))),
    )
    intent_value = str(intent)
    domain_value = str(chunk.domain)
    domain_boost = 0.0
    if (
        intent == KnowledgeIntent.PLATFORM_USAGE
        and domain_value == "assistant"
        or intent == KnowledgeIntent.APPROVAL
        and domain_value in {"assistant", "control_plane", "security"}
    ):
        domain_boost = 0.10
    elif intent_value in domain_value:
        domain_boost = 0.05
    authority_boost = 0.0
    if (
        intent == KnowledgeIntent.APPROVAL
        and chunk.path == "docs/AGENT_CONTROL_PLANE_ARCHITECTURE.md"
    ):
        authority_boost = 0.10
    if intent == KnowledgeIntent.PLATFORM_USAGE and chunk.path in {
        "docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md",
        "docs/AI_ASSISTANT_REAL_RUNTIME_GUIDE.md",
    }:
        authority_boost = 0.10
    score = heading + alias + command_path + overlap + domain_boost + authority_boost
    return min(1.0, score), matched


def _snippet(chunk: KnowledgeChunk, matched_terms: tuple[str, ...]) -> str:
    body = re.sub(r"\s+", " ", chunk.body).strip()
    if not matched_terms:
        return body[:900]
    lower = body.lower()
    positions = [
        lower.find(term.lower()) for term in matched_terms if lower.find(term.lower()) >= 0
    ]
    start = max(0, min(positions) - 180) if positions else 0
    return body[start : start + 900].strip()


def search_system_knowledge(
    request: KnowledgeSearchRequest,
    *,
    repo_root: Path,
    index_root: Path = DEFAULT_INDEX_ROOT,
) -> KnowledgeSearchResult:
    index_root = repo_root / index_root if not index_root.is_absolute() else index_root
    normalized = normalize_query(request.query)
    intent = request.intent_hint or classify_intent(normalized)
    query_hash = f"sha256:{sha256_text(request.query)}"
    manifest = load_manifest(index_root)
    if manifest is None:
        return KnowledgeSearchResult(
            status="blocked",
            intent=intent,
            queryHash=query_hash,
            normalizedQuery=normalized,
            hits=(),
            blockingReasons=("ASSISTANT_KNOWLEDGE_INDEX_MISSING",),
            generatedAtUtc=utc_now_iso(),
        )
    chunks = _load_chunks(index_root)
    scored: list[tuple[float, KnowledgeChunk, tuple[str, ...]]] = []
    for chunk in chunks:
        score, matched = _score_chunk(chunk, normalized, intent)
        if score > 0:
            scored.append((score, chunk, matched))
    scored.sort(key=lambda item: (-item[0], item[1].path, item[1].heading))
    hits = tuple(
        KnowledgeHit(
            chunkId=chunk.chunk_id,
            path=chunk.path,
            heading=chunk.heading,
            snippet=_snippet(chunk, matched),
            score=round(score, 4),
            matchedTerms=matched,
            commands=chunk.commands[:6],
            sourceHash=chunk.content_hash,
        )
        for score, chunk, matched in scored[: request.max_hits]
        if score >= 0.35
    )
    if not hits:
        return KnowledgeSearchResult(
            status="no_hits",
            intent=intent,
            queryHash=query_hash,
            normalizedQuery=normalized,
            hits=(),
            blockingReasons=("ASSISTANT_KNOWLEDGE_NO_VERIFIED_HITS",),
            generatedAtUtc=utc_now_iso(),
        )
    return KnowledgeSearchResult(
        status="ready",
        intent=intent,
        queryHash=query_hash,
        normalizedQuery=normalized,
        hits=hits,
        blockingReasons=(),
        generatedAtUtc=utc_now_iso(),
    )
