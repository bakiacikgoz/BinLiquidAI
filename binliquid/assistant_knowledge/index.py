from __future__ import annotations

import json
import subprocess
from pathlib import Path

from binliquid.assistant_knowledge.doc_loader import load_source_chunks
from binliquid.assistant_knowledge.models import (
    SystemKnowledgeDoctor,
    SystemKnowledgeManifest,
    sha256_text,
    utc_now_iso,
)
from binliquid.assistant_knowledge.source_registry import collect_knowledge_sources

DEFAULT_INDEX_ROOT = Path("artifacts/assistant-system-knowledge")
MANIFEST_NAME = "system_knowledge_manifest.json"
CHUNKS_NAME = "chunks.jsonl"


def _repo_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _manifest_hash(payload: dict[str, object]) -> str:
    stable = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{sha256_text(stable)}"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    temp.replace(path)


def build_system_knowledge_index(
    *,
    repo_root: Path,
    output_root: Path = DEFAULT_INDEX_ROOT,
    profile: str = "enterprise",
    force: bool = False,
) -> SystemKnowledgeManifest:
    _ = force
    output_root = repo_root / output_root if not output_root.is_absolute() else output_root
    sources = collect_knowledge_sources(repo_root=repo_root, profile=profile)
    blocking = tuple(
        "ASSISTANT_KNOWLEDGE_REQUIRED_SOURCE_MISSING"
        for source in sources
        if source.required and source.source_id.startswith("missing:")
    )
    chunks = tuple(
        chunk
        for source in sources
        if not source.source_id.startswith("missing:")
        for chunk in load_source_chunks(source, repo_root=repo_root)
    )
    source_count = len(
        [source for source in sources if not source.source_id.startswith("missing:")]
    )
    base_payload = {
        "profile": profile,
        "repoSha": _repo_sha(repo_root),
        "sources": [source.model_dump(mode="json", by_alias=True) for source in sources],
        "chunks": [chunk.model_dump(mode="json", by_alias=True) for chunk in chunks],
    }
    manifest = SystemKnowledgeManifest(
        profile=profile,
        status="blocked" if blocking else "ready",
        repoSha=str(base_payload["repoSha"]),
        sourceCount=source_count,
        chunkCount=len(chunks),
        manifestHash=_manifest_hash(base_payload),
        blockingReasons=tuple(sorted(set(blocking))),
        generatedAtUtc=utc_now_iso(),
        sources=sources,
    )
    _atomic_write(
        output_root / CHUNKS_NAME,
        "".join(
            json.dumps(
                chunk.model_dump(mode="json", by_alias=True),
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for chunk in chunks
        ),
    )
    _atomic_write(
        output_root / MANIFEST_NAME,
        json.dumps(
            manifest.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return manifest


def load_manifest(index_root: Path) -> dict[str, object] | None:
    manifest_path = index_root / MANIFEST_NAME
    if not manifest_path.exists():
        return None
    try:
        parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def doctor_system_knowledge(
    *,
    repo_root: Path,
    output_root: Path = DEFAULT_INDEX_ROOT,
    profile: str = "enterprise",
) -> SystemKnowledgeDoctor:
    output_root = repo_root / output_root if not output_root.is_absolute() else output_root
    manifest = load_manifest(output_root)
    current_sources = collect_knowledge_sources(repo_root=repo_root, profile=profile)
    missing_required = [
        source
        for source in current_sources
        if source.required and source.source_id.startswith("missing:")
    ]
    current_source_count = len(
        [source for source in current_sources if not source.source_id.startswith("missing:")]
    )
    blocking: list[str] = []
    if missing_required:
        blocking.append("ASSISTANT_KNOWLEDGE_REQUIRED_SOURCE_MISSING")
    if manifest is None:
        blocking.append("ASSISTANT_KNOWLEDGE_INDEX_MISSING")
        return SystemKnowledgeDoctor(
            profile=profile,
            status="missing" if not missing_required else "blocked",
            manifestExists=False,
            stale=False,
            requiredSourceMissingCount=len(missing_required),
            sourceCount=current_source_count,
            chunkCount=0,
            manifestHash=None,
            blockingReasons=tuple(sorted(set(blocking))),
            generatedAtUtc=utc_now_iso(),
        )
    manifest_sources = {
        str(source.get("path")): str(source.get("hashSha256"))
        for source in manifest.get("sources", [])
        if isinstance(source, dict)
    }
    current_hashes = {source.path: source.hash_sha256 for source in current_sources}
    stale = any(
        manifest_sources.get(path) != hash_value for path, hash_value in current_hashes.items()
    )
    if stale:
        blocking.append("ASSISTANT_KNOWLEDGE_INDEX_STALE")
    status = "blocked" if missing_required else "stale" if stale else "ready"
    return SystemKnowledgeDoctor(
        profile=profile,
        status=status,
        manifestExists=True,
        stale=stale,
        requiredSourceMissingCount=len(missing_required),
        sourceCount=int(manifest.get("sourceCount", 0)),
        chunkCount=int(manifest.get("chunkCount", 0)),
        manifestHash=str(manifest.get("manifestHash") or ""),
        blockingReasons=tuple(sorted(set(blocking))),
        generatedAtUtc=utc_now_iso(),
    )
