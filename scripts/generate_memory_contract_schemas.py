from __future__ import annotations

import json
from pathlib import Path

from binliquid.memory.models import (
    MemoryAuthoritySnapshot,
    MemoryEvidenceEvent,
    MemoryIndexStatus,
    MemoryPolicyDecision,
    MemoryRecordV3,
    MemoryRetrievalResult,
    MemoryWriteProposal,
)

SCHEMAS = {
    "memory_record_v3.schema.json": MemoryRecordV3,
    "memory_write_proposal.schema.json": MemoryWriteProposal,
    "memory_policy_decision.schema.json": MemoryPolicyDecision,
    "memory_retrieval_result.schema.json": MemoryRetrievalResult,
    "memory_evidence_event.schema.json": MemoryEvidenceEvent,
    "memory_index_status.schema.json": MemoryIndexStatus,
    "memory_authority_snapshot.schema.json": MemoryAuthoritySnapshot,
}


def main() -> None:
    output_dir = Path("contracts/memory")
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        schema = model.model_json_schema(by_alias=True)
        (output_dir / filename).write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
