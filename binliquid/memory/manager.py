from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from binliquid.memory.persistent_store import PersistentMemoryStore
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
        store: PersistentMemoryStore,
        gate: SalienceGate,
        max_rows: int = 5000,
    ):
        self.enabled = enabled
        self.store = store
        self.gate = gate
        self.max_rows = max_rows

    def maybe_write(
        self,
        *,
        session_id: str,
        task_type: str,
        user_input: str,
        assistant_output: str,
        expert_payload: dict[str, object] | None = None,
    ) -> MemoryWriteResult:
        if not self.enabled:
            return MemoryWriteResult(
                written=False,
                salience_score=0.0,
                reason="memory_disabled",
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

        content = (
            f"User: {user_input}\n"
            f"Assistant: {assistant_output}"
        )
        record_id = self.store.write(
            session_id=session_id,
            task_type=task_type,
            content=content,
            salience=decision.salience_score,
            metadata={"event_id": str(uuid4())},
        )
        self.store.prune_to_limit(self.max_rows)
        return MemoryWriteResult(
            written=True,
            salience_score=decision.salience_score,
            reason=decision.reason,
            record_id=record_id,
        )

    def context_snippets(self, query: str, limit: int = 4) -> list[str]:
        if not self.enabled:
            return []
        records = self.store.search(keyword=query, limit=limit)
        return [record.content for record in records]

    def stats(self) -> dict[str, int | bool]:
        return {
            "enabled": self.enabled,
            "total_records": self.store.count(),
            "max_rows": self.max_rows,
        }
