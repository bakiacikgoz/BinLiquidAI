from __future__ import annotations

from typing import Any

from binliquid.assistant_knowledge.models import (
    KnowledgeHit,
    KnowledgeIntent,
    KnowledgeSearchResult,
    sha256_text,
)

FIXTURE_GENERATED_AT = "2026-01-01T00:00:00Z"


def agent_task_search_result_fixture() -> KnowledgeSearchResult:
    query = "AgeisOs sisteminde nasil bir agent'e gorev verebilirim?"
    return KnowledgeSearchResult(
        status="ready",
        intent=KnowledgeIntent.AGENT_TASK,
        queryHash=f"sha256:{sha256_text(query)}",
        normalizedQuery="aegisos sisteminde nasil bir agent e gorev verebilirim",
        hits=(
            KnowledgeHit(
                chunkId="docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md#external-agent-gateway-guide",
                path="docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md",
                heading="External Agent Gateway Guide",
                snippet=(
                    "Register the external agent in Control Plane, then submit governed requests "
                    "through the external agent gateway. External writes require approval evidence."
                ),
                score=0.93,
                matchedTerms=("agent", "gateway", "gorev"),
                commands=(
                    "uv run binliquid control-plane agent register "
                    "--spec examples/agents/local_stdio_agent.json --json",
                    "uv run binliquid external-agent gateway submit-v1-1 "
                    "--request examples/external_agent/read_only_request.json --json",
                ),
                sourceHash="sha256:fixture-external-agent-gateway",
            ),
        ),
        blockingReasons=(),
        generatedAtUtc=FIXTURE_GENERATED_AT,
    )


def unknown_query_search_result_fixture() -> KnowledgeSearchResult:
    query = "unrelated sourdough bread timing"
    return KnowledgeSearchResult(
        status="no_hits",
        intent=KnowledgeIntent.UNKNOWN,
        queryHash=f"sha256:{sha256_text(query)}",
        normalizedQuery=query,
        hits=(),
        blockingReasons=("ASSISTANT_KNOWLEDGE_NO_VERIFIED_HITS",),
        generatedAtUtc=FIXTURE_GENERATED_AT,
    )


def contract_fixtures() -> dict[str, dict[str, Any]]:
    return {
        "system_knowledge_agent_task_pass.json": agent_task_search_result_fixture().model_dump(
            mode="json",
            by_alias=True,
        ),
        "system_knowledge_unknown_query.json": unknown_query_search_result_fixture().model_dump(
            mode="json",
            by_alias=True,
        ),
    }
