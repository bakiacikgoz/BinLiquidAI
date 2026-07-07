from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.assistant_tasking.fixtures import contract_fixtures  # noqa: E402
from binliquid.assistant_tasking.models import (  # noqa: E402
    AssistantTaskPlan,
    AssistantTaskStatus,
    AssistantTaskSubmissionResult,
)

SCHEMAS = {
    "assistant_task_plan": AssistantTaskPlan,
    "assistant_task_submission": AssistantTaskSubmissionResult,
    "assistant_task_status": AssistantTaskStatus,
}


def main() -> None:
    root = REPO_ROOT / "contracts" / "assistant_tasking"
    root.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (root / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
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
