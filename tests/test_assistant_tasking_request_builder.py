from __future__ import annotations

from pathlib import Path

from binliquid.assistant_tasking.models import (
    AssistantTaskPlanRequest,
    AssistantTaskSubmissionRequest,
)
from binliquid.assistant_tasking.request_builder import build_external_agent_request
from binliquid.assistant_tasking.service import plan_task
from binliquid.assistant_tasking.store import AssistantTaskStore
from binliquid.control_plane.registry import AgentRegistry, load_agent_spec
from tests.test_external_agent_gateway_v1_1 import _bind_enrollment

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_request_builder_requires_matching_plan_hash(tmp_path: Path) -> None:
    root_dir = tmp_path / "cp"
    registry = AgentRegistry(root_dir=root_dir)
    registry.register(
        load_agent_spec(REPO_ROOT / "examples/control_plane/agent_external_gateway.yaml"),
        actor="test",
    )
    _bind_enrollment(registry=registry, root_dir=root_dir)
    plan = plan_task(
        AssistantTaskPlanRequest(message="son servis uyarilarini incele", rootDir=str(root_dir)),
        store=AssistantTaskStore(tmp_path / "tasking"),
    )

    request = build_external_agent_request(
        plan,
        AssistantTaskSubmissionRequest(
            proposalId=plan.proposal_id,
            confirmPlanHash=plan.plan_hash,
            operatorId="operator-local",
            rootDir=str(root_dir),
        ),
    )

    assert request.agent_id == "external-agent"
    assert request.risk_hint == "read_only"
