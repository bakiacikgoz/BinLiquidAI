from __future__ import annotations

from binliquid.assistant_knowledge.answer_policy import ANSWER_RULES, IDENTITY_BRIEF
from binliquid.assistant_knowledge.models import (
    AssistantSystemKnowledgeContext,
    KnowledgeSearchResult,
)


def build_system_knowledge_context(
    result: KnowledgeSearchResult,
    *,
    max_chars: int = 8000,
) -> AssistantSystemKnowledgeContext:
    if result.status != "ready":
        return AssistantSystemKnowledgeContext(
            status="blocked" if result.status == "blocked" else "unavailable",
            identityBrief=IDENTITY_BRIEF,
            answerRules=ANSWER_RULES,
            sources=(),
            contextText=(
                "Local AegisOS system knowledge is not available for this query. "
                "Do not guess platform behavior. Suggested command: "
                "uv run binliquid assistant knowledge build --profile enterprise --json"
            ),
            omittedSources=(),
            blockingReasons=result.blocking_reasons,
        )
    lines = [
        "Use the following local AegisOS/BinLiquid system knowledge as grounded context.",
        "Cite source paths in the answer when making platform claims.",
    ]
    omitted: list[str] = []
    used = []
    for hit in result.hits:
        entry = [
            f"Source: {hit.path}",
            f"Heading: {hit.heading}",
            f"Score: {hit.score}",
            f"Snippet: {hit.snippet}",
        ]
        if hit.commands:
            entry.append("Commands: " + " | ".join(hit.commands[:4]))
        candidate = "\n".join(entry)
        if sum(len(line) + 2 for line in lines) + len(candidate) > max_chars:
            omitted.append(hit.chunk_id)
            continue
        lines.append(candidate)
        used.append(hit)
    return AssistantSystemKnowledgeContext(
        status="available",
        identityBrief=IDENTITY_BRIEF,
        answerRules=ANSWER_RULES,
        sources=tuple(used),
        contextText="\n\n".join(lines),
        omittedSources=tuple(omitted),
        blockingReasons=(),
    )
