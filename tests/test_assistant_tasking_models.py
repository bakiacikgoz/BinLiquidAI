from __future__ import annotations

from binliquid.assistant_tasking.fixtures import contract_fixtures
from binliquid.assistant_tasking.models import AssistantTaskPlan, AssistantTaskSubmissionResult


def test_assistant_tasking_contract_fixtures_validate() -> None:
    fixtures = contract_fixtures()

    AssistantTaskPlan.model_validate(fixtures["read_only_plan_pass.json"])
    AssistantTaskPlan.model_validate(fixtures["write_requires_approval.json"])
    AssistantTaskPlan.model_validate(fixtures["destructive_denied.json"])
    AssistantTaskSubmissionResult.model_validate(fixtures["idempotency_conflict_blocked.json"])
    assert fixtures["read_only_plan_pass.json"]["safeToSubmit"] is True
    assert fixtures["destructive_denied.json"]["safeToSubmit"] is False
