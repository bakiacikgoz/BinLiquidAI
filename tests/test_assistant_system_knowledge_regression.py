from __future__ import annotations

import json
from pathlib import Path

from binliquid.assistant_knowledge.index import build_system_knowledge_index
from binliquid.assistant_knowledge.models import KnowledgeSearchRequest
from binliquid.assistant_knowledge.retriever import search_system_knowledge

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "benchmarks" / "tasks" / "assistant" / "system_knowledge_queries.jsonl"


def _records() -> list[dict[str, object]]:
    return [json.loads(line) for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines()]


def test_system_knowledge_regression_queries_are_grounded(tmp_path: Path) -> None:
    build_system_knowledge_index(repo_root=REPO_ROOT, output_root=tmp_path, profile="enterprise")
    for record in _records():
        result = search_system_knowledge(
            KnowledgeSearchRequest(query=str(record["query"]), profile="enterprise"),
            repo_root=REPO_ROOT,
            index_root=tmp_path,
        )
        assert result.status == "ready", record["id"]
        assert result.intent == record["expectedIntent"]
        paths = {hit.path for hit in result.hits}
        assert set(record["expectedSources"]).issubset(paths), record["id"]
        rendered = " ".join(hit.snippet for hit in result.hits)
        for forbidden in record["forbiddenTerms"]:
            assert str(forbidden).lower() not in rendered.lower(), record["id"]
