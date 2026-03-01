from __future__ import annotations

from datetime import UTC, datetime

from binliquid.memory.persistent_store import MemoryRecord


def rank_records(records: list[MemoryRecord]) -> list[MemoryRecord]:
    now = datetime.now(UTC)

    def score(record: MemoryRecord) -> float:
        try:
            created = datetime.fromisoformat(record.created_at.replace("Z", "+00:00"))
        except ValueError:
            created = now
        age_h = max((now - created).total_seconds() / 3600, 0.0)
        recency = 1 / (1 + age_h / 24)
        return (record.salience * 0.7) + (recency * 0.3)

    return sorted(records, key=score, reverse=True)
