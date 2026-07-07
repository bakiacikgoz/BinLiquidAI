from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from binliquid.assistant_tasking.models import (
    AssistantTaskPlan,
    AssistantTaskStatus,
    AssistantTaskSubmissionResult,
)

DEFAULT_TASKING_ROOT = Path("artifacts/assistant-tasking")


class AssistantTaskStore:
    def __init__(self, root: str | Path = DEFAULT_TASKING_ROOT):
        self.root = Path(root)

    def write_plan(self, plan: AssistantTaskPlan) -> str:
        path = self.root / "proposals" / f"{plan.proposal_id}.json"
        self._write_json(path, plan.model_dump(mode="json", by_alias=True))
        return _relative_or_str(path)

    def read_plan(self, proposal_id: str) -> AssistantTaskPlan | None:
        path = self.root / "proposals" / f"{proposal_id}.json"
        if not path.exists():
            return None
        return AssistantTaskPlan.model_validate_json(path.read_text(encoding="utf-8"))

    def write_submission(self, result: AssistantTaskSubmissionResult) -> str:
        path = self.root / "submissions" / f"{result.proposal_id}.json"
        self._write_json(path, result.model_dump(mode="json", by_alias=True))
        return _relative_or_str(path)

    def read_submission(self, proposal_id: str) -> AssistantTaskSubmissionResult | None:
        path = self.root / "submissions" / f"{proposal_id}.json"
        if not path.exists():
            return None
        return AssistantTaskSubmissionResult.model_validate_json(path.read_text(encoding="utf-8"))

    def status(self, proposal_id: str) -> AssistantTaskStatus:
        plan = self.read_plan(proposal_id)
        submission = self.read_submission(proposal_id)
        if plan is None:
            return AssistantTaskStatus(
                proposalId=proposal_id,
                status="missing",
                blockingReasons=("ASSISTANT_TASK_PROPOSAL_MISSING",),
            )
        refs = [f"artifacts/assistant-tasking/proposals/{proposal_id}.json"]
        if submission is not None:
            refs.append(f"artifacts/assistant-tasking/submissions/{proposal_id}.json")
            if submission.evidence_ref:
                refs.append(submission.evidence_ref)
        return AssistantTaskStatus(
            proposalId=proposal_id,
            status=submission.status if submission else plan.status,
            plan=plan,
            submission=submission,
            evidenceRefs=tuple(refs),
        )

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp.replace(path)


def _relative_or_str(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return str(path)
