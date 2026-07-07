from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.assistant_knowledge.fixtures import contract_fixtures  # noqa: E402
from binliquid.assistant_knowledge.models import (  # noqa: E402
    AssistantSystemKnowledgeContext,
    KnowledgeSearchResult,
    SystemKnowledgeManifest,
)

SCHEMAS = {
    "system_knowledge_manifest": SystemKnowledgeManifest,
    "system_knowledge_search_result": KnowledgeSearchResult,
    "system_knowledge_context": AssistantSystemKnowledgeContext,
}


def main() -> None:
    root = REPO_ROOT / "contracts" / "assistant"
    root.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (root / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    fixture_root = root / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=True)
    for name, payload in contract_fixtures().items():
        (fixture_root / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
