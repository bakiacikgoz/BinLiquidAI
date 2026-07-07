from __future__ import annotations

import json
from pathlib import Path

from binliquid.assistant_knowledge.context_pack import build_system_knowledge_context
from binliquid.assistant_knowledge.doc_loader import load_source_chunks, redact_unsafe_text
from binliquid.assistant_knowledge.fixtures import contract_fixtures
from binliquid.assistant_knowledge.index import (
    build_system_knowledge_index,
    doctor_system_knowledge,
)
from binliquid.assistant_knowledge.models import KnowledgeSearchRequest
from binliquid.assistant_knowledge.retriever import normalize_query, search_system_knowledge
from binliquid.assistant_knowledge.source_registry import (
    collect_knowledge_sources,
    is_excluded_path,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "benchmarks" / "tasks" / "assistant" / "system_knowledge_queries.jsonl"


def test_regression_fixture_parses() -> None:
    records = [json.loads(line) for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()]
    assert {record["id"] for record in records} >= {
        "agent_task_tr",
        "knowledge_origin_tr",
        "computer_use_boundary_tr",
    }
    assert all(record["query"] for record in records)
    assert all(record["expectedSources"] for record in records)


def test_contract_fixtures_cover_agent_task_and_unknown_query() -> None:
    fixtures = contract_fixtures()

    assert set(fixtures) == {
        "system_knowledge_agent_task_pass.json",
        "system_knowledge_unknown_query.json",
    }
    assert fixtures["system_knowledge_agent_task_pass.json"]["status"] == "ready"
    assert fixtures["system_knowledge_agent_task_pass.json"]["intent"] == "agent_task"
    assert fixtures["system_knowledge_unknown_query.json"]["status"] == "no_hits"


def test_source_registry_includes_required_docs_and_excludes_private_paths() -> None:
    sources = collect_knowledge_sources(repo_root=REPO_ROOT, profile="enterprise")
    paths = {source.path for source in sources}
    assert "docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md" in paths
    assert "docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md" in paths
    assert "docs/AGENT_CONTROL_PLANE_ADAPTER_CONTRACT.md" in paths
    assert not any(path.startswith("artifacts/") for path in paths)
    assert not any(path.startswith(".binliquid/") for path in paths)
    assert is_excluded_path(
        REPO_ROOT / "artifacts" / "assistant-system-knowledge" / "chunks.jsonl",
        REPO_ROOT,
    )


def test_markdown_loader_extracts_headings_commands_and_redacts() -> None:
    source = next(
        item
        for item in collect_knowledge_sources(repo_root=REPO_ROOT, profile="enterprise")
        if item.path == "docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md"
    )
    chunks = load_source_chunks(source, repo_root=REPO_ROOT)
    assert chunks
    assert any(chunk.heading == "Giving An Agent A Task" for chunk in chunks)
    assert any(
        "uv run binliquid control-plane agent register" in command
        for chunk in chunks
        for command in chunk.commands
    )
    assert "sk-" not in redact_unsafe_text("token=sk-abcdefghijklmnopqrstuvwxyz")
    assert "[redacted-secret]" in redact_unsafe_text("token=sk-abcdefghijklmnopqrstuvwxyz")


def test_build_index_is_deterministic_and_searches_agent_task(tmp_path: Path) -> None:
    first = build_system_knowledge_index(
        repo_root=REPO_ROOT,
        output_root=tmp_path,
        profile="enterprise",
    )
    second = build_system_knowledge_index(
        repo_root=REPO_ROOT,
        output_root=tmp_path,
        profile="enterprise",
    )
    assert first.status == "ready"
    assert first.source_count > 0
    assert first.chunk_count > 0
    assert first.manifest_hash == second.manifest_hash

    result = search_system_knowledge(
        KnowledgeSearchRequest(
            query="AgeisOs sisteminde nasıl bir agent'e görev verebilirim?",
            profile="enterprise",
        ),
        repo_root=REPO_ROOT,
        index_root=tmp_path,
    )
    assert result.status == "ready"
    assert result.intent == "agent_task"
    hit_paths = {hit.path for hit in result.hits}
    assert "docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md" in hit_paths
    assert "docs/AGENT_CONTROL_PLANE_ADAPTER_CONTRACT.md" in hit_paths
    rendered = " ".join(hit.snippet for hit in result.hits)
    assert "SIEM" not in rendered
    assert "XDR" not in rendered


def test_query_alias_and_no_hits_fail_closed(tmp_path: Path) -> None:
    build_system_knowledge_index(repo_root=REPO_ROOT, output_root=tmp_path, profile="enterprise")
    assert normalize_query("AgeisOs agent görev") == "aegisos agent gorev"
    result = search_system_knowledge(
        KnowledgeSearchRequest(query="unrelated sourdough bread timing", profile="enterprise"),
        repo_root=REPO_ROOT,
        index_root=tmp_path,
    )
    assert result.status == "no_hits"
    assert "ASSISTANT_KNOWLEDGE_NO_VERIFIED_HITS" in result.blocking_reasons


def test_context_pack_cites_local_sources(tmp_path: Path) -> None:
    build_system_knowledge_index(repo_root=REPO_ROOT, output_root=tmp_path, profile="enterprise")
    result = search_system_knowledge(
        KnowledgeSearchRequest(query="Bunu nereden biliyorsun?", profile="enterprise"),
        repo_root=REPO_ROOT,
        index_root=tmp_path,
    )
    context = build_system_knowledge_context(result)
    assert context.status == "available"
    assert "local AegisOS/BinLiquid system knowledge" in context.context_text
    assert context.sources


def test_doctor_reports_missing_index(tmp_path: Path) -> None:
    doctor = doctor_system_knowledge(
        repo_root=REPO_ROOT,
        output_root=tmp_path,
        profile="enterprise",
    )
    assert doctor.status == "missing"
    assert "ASSISTANT_KNOWLEDGE_INDEX_MISSING" in doctor.blocking_reasons
