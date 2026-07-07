from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

from binliquid.assistant_knowledge.models import KnowledgeChunk, KnowledgeSource, sha256_text

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{12,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
)
COMMAND_RE = re.compile(r"(?m)^\s*(uv run|binliquid|aegis|make|corepack|cargo|python)\b.+$")
REASON_RE = re.compile(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+){2,}\b")


def redact_unsafe_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[redacted-secret]", redacted)
    return redacted


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _aliases_for(path: str, heading: str, body: str) -> tuple[str, ...]:
    haystack = f"{path} {heading} {body}".lower()
    aliases: set[str] = {"aegisos", "binliquid", "agent control plane"}
    if "external" in haystack or "gateway" in haystack:
        aliases.update({"agent task", "gorev", "görev", "external agent gateway"})
    if "assistant" in haystack or "system knowledge" in haystack:
        aliases.update({"nereden biliyorsun", "where do you know", "local system knowledge"})
    if "approval" in haystack:
        aliases.add("approval")
    if "computer" in haystack:
        aliases.update({"computer use", "computer-use"})
    if "provider" in haystack:
        aliases.add("provider")
    if "memory" in haystack:
        aliases.add("memory")
    return tuple(sorted(aliases))


def _chunk(source: KnowledgeSource, index: int, heading: str, body: str) -> KnowledgeChunk:
    clipped = redact_unsafe_text(body.strip())[:6000]
    commands = tuple(
        dict.fromkeys(match.group(0).strip() for match in COMMAND_RE.finditer(clipped))
    )
    reason_codes = tuple(sorted(set(REASON_RE.findall(clipped))))
    chunk_key = f"{source.path}#{index}:{heading}".strip(":")
    return KnowledgeChunk(
        chunkId=f"{source.path}#{sha256_text(chunk_key)[:12]}",
        sourceId=source.source_id,
        path=source.path,
        heading=heading[:240],
        body=clipped or heading or source.path,
        aliases=_aliases_for(source.path, heading, clipped),
        domain=source.domain,
        commands=commands[:12],
        reasonCodes=reason_codes[:30],
        contentHash=sha256_text(f"{source.path}\n{heading}\n{clipped}"),
    )


def _markdown_sections(text: str) -> Iterable[tuple[str, str]]:
    current_heading = "Overview"
    body: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            if body:
                yield current_heading, "\n".join(body)
            current_heading = heading.group(2).strip()
            body = [line]
        else:
            body.append(line)
    if body:
        yield current_heading, "\n".join(body)


def _json_schema_summary(text: str) -> tuple[str, str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return "JSON source", text[:6000]
    title = str(parsed.get("title") or parsed.get("$id") or "JSON schema")
    properties = parsed.get("properties")
    keys = sorted(properties) if isinstance(properties, dict) else []
    body = json.dumps(
        {
            "title": title,
            "required": parsed.get("required", []),
            "properties": keys[:80],
        },
        ensure_ascii=False,
        indent=2,
    )
    return title, body


def load_source_chunks(source: KnowledgeSource, *, repo_root: Path) -> tuple[KnowledgeChunk, ...]:
    path = repo_root / source.path
    if not path.exists() or not path.is_file() or source.source_id.startswith("missing:"):
        return ()
    text = _read_text(path)
    chunks: list[KnowledgeChunk] = []
    if str(source.kind) == "json_schema":
        heading, body = _json_schema_summary(text)
        chunks.append(_chunk(source, 0, heading, body))
    elif str(source.kind) == "markdown":
        for index, (heading, body) in enumerate(_markdown_sections(text)):
            if body.strip():
                chunks.append(_chunk(source, index, heading, body))
    else:
        lines = text.splitlines()
        for index in range(0, max(1, len(lines)), 160):
            body = "\n".join(lines[index : index + 160])
            chunks.append(_chunk(source, index // 160, path.name, body))
    return tuple(chunk for chunk in chunks if chunk.body.strip())
