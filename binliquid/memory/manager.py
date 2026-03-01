from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from binliquid.memory.persistent_store import PersistentMemoryStore
from binliquid.memory.retrieval_ranker import rank_records
from binliquid.memory.salience_gate import SalienceDecision, SalienceGate


@dataclass(slots=True)
class MemoryWriteResult:
    written: bool
    salience_score: float
    reason: str
    record_id: int | None


class MemoryManager:
    """Coordinates salience gating and persistent memory writes."""

    def __init__(
        self,
        *,
        enabled: bool,
        store: PersistentMemoryStore | None,
        gate: SalienceGate,
        max_rows: int = 5000,
        ttl_days: int = 30,
        rank_salience_weight: float = 0.7,
        rank_recency_weight: float = 0.3,
    ):
        self.enabled = enabled
        self.store = store
        self.gate = gate
        self.max_rows = max_rows
        self.ttl_days = ttl_days
        self.rank_salience_weight = rank_salience_weight
        self.rank_recency_weight = rank_recency_weight
        self._write_attempts = 0
        self._writes_accepted = 0
        self._dedup_hits = 0
        self._retrieval_queries = 0
        self._retrieval_hits = 0
        self._retrieval_useful = 0

    def maybe_write(
        self,
        *,
        session_id: str,
        task_type: str,
        user_input: str,
        assistant_output: str,
        expert_payload: dict[str, object] | None = None,
    ) -> MemoryWriteResult:
        self._write_attempts += 1
        if not self.enabled:
            return MemoryWriteResult(
                written=False,
                salience_score=0.0,
                reason="memory_disabled",
                record_id=None,
            )
        if self.store is None:
            return MemoryWriteResult(
                written=False,
                salience_score=0.0,
                reason="memory_store_missing",
                record_id=None,
            )

        decision: SalienceDecision = self.gate.evaluate(
            task_type=task_type,
            user_input=user_input,
            assistant_output=assistant_output,
            expert_payload=expert_payload,
        )
        if not decision.should_write:
            return MemoryWriteResult(
                written=False,
                salience_score=decision.salience_score,
                reason=decision.reason,
                record_id=None,
            )

        content = f"User: {user_input}\nAssistant: {assistant_output}"
        status = self.store.write_with_status(
            session_id=session_id,
            task_type=task_type,
            content=content,
            salience=decision.salience_score,
            metadata={"event_id": str(uuid4())},
            ttl_days=self.ttl_days,
        )
        record_id = status.record_id
        self._writes_accepted += 1
        if status.dedup_hit:
            self._dedup_hits += 1
        self.store.prune_to_limit(self.max_rows)
        return MemoryWriteResult(
            written=True,
            salience_score=decision.salience_score,
            reason=decision.reason,
            record_id=record_id,
        )

    def context_snippets(self, query: str, limit: int = 4) -> list[str]:
        if not self.enabled or self.store is None:
            return []
        self._retrieval_queries += 1
        records = self.store.search(keyword=query, limit=max(limit * 2, limit))
        if records:
            self._retrieval_hits += 1
        ranked = rank_records(
            records,
            salience_weight=self.rank_salience_weight,
            recency_weight=self.rank_recency_weight,
        )
        snippets = [record.content for record in ranked[:limit]]
        if snippets:
            self._retrieval_useful += 1
        return snippets

    def stats(self) -> dict[str, int | bool | float]:
        total_records = self.store.count() if self.store is not None else 0
        write_rate = (
            round(self._writes_accepted / max(self._write_attempts, 1), 4)
            if self._write_attempts
            else 0.0
        )
        dedup_hit_rate = (
            round(self._dedup_hits / max(self._writes_accepted, 1), 4)
            if self._writes_accepted
            else 0.0
        )
        retrieval_hit_rate = (
            round(self._retrieval_hits / max(self._retrieval_queries, 1), 4)
            if self._retrieval_queries
            else 0.0
        )
        retrieval_usefulness_rate = (
            round(self._retrieval_useful / max(self._retrieval_queries, 1), 4)
            if self._retrieval_queries
            else 0.0
        )
        stale_ratio = (
            round(1.0 - retrieval_usefulness_rate, 4) if self._retrieval_queries else 0.0
        )
        return {
            "enabled": self.enabled,
            "total_records": total_records,
            "max_rows": self.max_rows,
            "ttl_days": self.ttl_days,
            "memory_write_rate": write_rate,
            "dedup_hit_rate": dedup_hit_rate,
            "retrieval_hit_rate": retrieval_hit_rate,
            "retrieval_usefulness_rate": retrieval_usefulness_rate,
            "stale_retrieval_ratio": stale_ratio,
            "rank_salience_weight": round(self.rank_salience_weight, 4),
            "rank_recency_weight": round(self.rank_recency_weight, 4),
        }
