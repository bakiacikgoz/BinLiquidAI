from __future__ import annotations

import hashlib
from pathlib import Path

from binliquid.assistant_knowledge.models import (
    KnowledgeDomain,
    KnowledgeSource,
    KnowledgeSourceKind,
)

REQUIRED_SOURCE_PATHS = (
    "docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md",
    "docs/PRODUCT_COMPLETE_SCOPE.md",
    "docs/AI_ASSISTANT_REAL_RUNTIME_GUIDE.md",
    "docs/AGENT_CONTROL_PLANE_ARCHITECTURE.md",
    "docs/AGENT_CONTROL_PLANE_ADAPTER_CONTRACT.md",
    "docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md",
    "docs/PRODUCT_COMPLETE_NO_SHIP_REGISTER.md",
    "docs/RFC_MODEL_PROVIDER_GOVERNANCE_001.md",
    "docs/MEMORY_RUNTIME_INTEGRATION.md",
    "docs/COMPUTER_USE_SECURITY_BOUNDARY.md",
)

OPTIONAL_SOURCE_PATHS = (
    "docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE_RUNBOOK.md",
    "docs/AI_ASSISTANT_OPERATOR_GUIDE.md",
    "docs/MODEL_PROVIDER_OPERATOR_GUIDE.md",
    "docs/COMPUTER_USE_OPERATOR_RUNBOOK.md",
    "Makefile",
    "apps/operator-panel/src/routeCapabilityMatrix.ts",
    "apps/operator-panel/src/routeRegistry.ts",
    "apps/operator-panel/src/i18n.ts",
    "binliquid/cli.py",
)

EXCLUDED_PARTS = {
    ".git",
    ".binliquid",
    "artifacts",
    "node_modules",
    "target",
    "target-codex-test",
    "__pycache__",
}


def _repo_relative(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _kind_for(path: str) -> KnowledgeSourceKind:
    if path == "Makefile":
        return KnowledgeSourceKind.MAKEFILE
    if path.endswith(".schema.json"):
        return KnowledgeSourceKind.JSON_SCHEMA
    if path.endswith((".yaml", ".yml")):
        return KnowledgeSourceKind.YAML_EXAMPLE
    if path.endswith(".ts") or path.endswith(".tsx"):
        return KnowledgeSourceKind.TS_SOURCE
    if path.endswith(".py"):
        return KnowledgeSourceKind.PY_CLI
    return KnowledgeSourceKind.MARKDOWN


def _domain_for(path: str) -> KnowledgeDomain:
    lower = path.lower()
    if "computer_use" in lower or "computer-use" in lower:
        return KnowledgeDomain.COMPUTER_USE
    if "provider" in lower:
        return KnowledgeDomain.PROVIDER
    if "memory" in lower:
        return KnowledgeDomain.MEMORY
    if "security" in lower or "no_ship" in lower:
        return KnowledgeDomain.SECURITY
    if "operator-panel" in lower or "route" in lower or "i18n" in lower:
        return KnowledgeDomain.UI
    if "assistant" in lower:
        return KnowledgeDomain.ASSISTANT
    if "deploy" in lower or "makefile" in lower:
        return KnowledgeDomain.DEPLOYMENT
    return KnowledgeDomain.CONTROL_PLANE


def is_excluded_path(path: Path, repo_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return True
    parts = set(relative.parts)
    if parts.intersection(EXCLUDED_PARTS):
        return True
    name = path.name.lower()
    return (
        name.startswith(".env")
        or name.endswith((".log", ".pem", ".key", ".p12", ".pfx"))
        or "secret" in name
    )


def collect_knowledge_sources(
    *,
    repo_root: Path,
    profile: str = "enterprise",
) -> tuple[KnowledgeSource, ...]:
    _ = profile
    paths: list[tuple[str, bool]] = [(path, True) for path in REQUIRED_SOURCE_PATHS]
    paths.extend((path, False) for path in OPTIONAL_SOURCE_PATHS)
    paths.extend(
        (path.relative_to(repo_root).as_posix(), False)
        for path in sorted((repo_root / "contracts").glob("**/*.schema.json"))
        if not is_excluded_path(path, repo_root)
    )
    paths.extend(
        (path.relative_to(repo_root).as_posix(), False)
        for root in (repo_root / "examples",)
        if root.exists()
        for path in sorted(root.glob("**/*"))
        if path.suffix.lower() in {".yaml", ".yml", ".json", ".py"}
        and not is_excluded_path(path, repo_root)
    )

    seen: set[str] = set()
    sources: list[KnowledgeSource] = []
    for relative_path, required in paths:
        normalized = relative_path.replace("\\", "/")
        if normalized in seen:
            continue
        seen.add(normalized)
        path = repo_root / normalized
        if not path.exists() or not path.is_file() or is_excluded_path(path, repo_root):
            if required:
                sources.append(
                    KnowledgeSource(
                        sourceId=f"missing:{normalized}",
                        path=normalized,
                        kind=_kind_for(normalized),
                        domain=_domain_for(normalized),
                        required=True,
                        hashSha256="0" * 64,
                        lastModified=None,
                    )
                )
            continue
        sources.append(
            KnowledgeSource(
                sourceId=_repo_relative(path, repo_root),
                path=_repo_relative(path, repo_root),
                kind=_kind_for(normalized),
                domain=_domain_for(normalized),
                required=required,
                hashSha256=_hash_file(path),
                lastModified=None,
            )
        )
    return tuple(sorted(sources, key=lambda item: item.path))
