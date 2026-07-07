from __future__ import annotations

from pathlib import Path

from binliquid.assistant_tasking.models import (
    AssistantTaskPlanRequest,
    AssistantTaskSubmissionRequest,
)
from binliquid.assistant_tasking.service import plan_task, submit_task
from binliquid.assistant_tasking.store import AssistantTaskStore
from binliquid.control_plane.registry import AgentRegistry, load_agent_spec
from tests.test_external_agent_gateway_v1_1 import _bind_enrollment

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_service_read_only_submit_and_idempotent_replay(tmp_path: Path) -> None:
    root_dir = _root_with_enrolled_agent(tmp_path)
    store = AssistantTaskStore(tmp_path / "tasking")
    plan = plan_task(
        AssistantTaskPlanRequest(
            message="Governed ops agent'e son servis uyarilarini inceleme gorevi ver.",
            rootDir=str(root_dir),
        ),
        store=store,
    )
    first = submit_task(_submit_request(plan, root_dir), store=store)
    second = submit_task(_submit_request(plan, root_dir), store=store)

    assert plan.status == "planned"
    assert plan.safe_to_submit is True
    assert first.status == "accepted"
    assert first.run_id is not None
    assert first.evidence_ref is not None
    assert second.status == "accepted"
    assert second.idempotency_status == "replayed"
    assert second.run_id == first.run_id


def test_service_write_requires_approval_and_destructive_is_not_submitted(tmp_path: Path) -> None:
    root_dir = _root_with_enrolled_agent(tmp_path)
    store = AssistantTaskStore(tmp_path / "tasking")
    write = plan_task(
        AssistantTaskPlanRequest(
            message="External Gateway Agent musteri destek sisteminde takip ticket'i acsin.",
            rootDir=str(root_dir),
        ),
        store=store,
    )
    write_result = submit_task(_submit_request(write, root_dir), store=store)
    destructive = plan_task(
        AssistantTaskPlanRequest(
            message="External agent eski kayitlari silsin.",
            rootDir=str(root_dir),
        ),
        store=store,
    )
    denied = submit_task(_submit_request(destructive, root_dir), store=store)

    assert write.policy_preview.decision == "require_approval"
    assert write_result.status == "blocked_pending_approval"
    assert write_result.approval_id is not None
    assert destructive.safe_to_submit is False
    assert "ASSISTANT_TASK_DESTRUCTIVE_DENIED" in destructive.blocked_reasons
    assert denied.status == "denied"
    assert denied.run_id is None


def test_service_unknown_and_unenrolled_agents_fail_closed(tmp_path: Path) -> None:
    root_dir = tmp_path / "cp"
    registry = AgentRegistry(root_dir=root_dir)
    registry.register(
        load_agent_spec(REPO_ROOT / "examples/control_plane/agent_external_gateway.yaml"),
        actor="test",
    )
    store = AssistantTaskStore(tmp_path / "tasking")

    unknown = plan_task(
        AssistantTaskPlanRequest(message="Bilinmeyen-agent'a gorev ver.", rootDir=str(root_dir)),
        store=store,
    )
    unenrolled = plan_task(
        AssistantTaskPlanRequest(
            message="Enrolled olmayan external agent ile oku.",
            rootDir=str(root_dir),
        ),
        store=store,
    )

    assert unknown.safe_to_submit is False
    assert "ASSISTANT_TASK_UNKNOWN_AGENT_DENIED" in unknown.blocked_reasons
    assert unenrolled.safe_to_submit is False
    assert "ASSISTANT_TASK_UNENROLLED_AGENT_DENIED" in unenrolled.blocked_reasons


def _root_with_enrolled_agent(tmp_path: Path) -> Path:
    root_dir = tmp_path / "cp"
    registry = AgentRegistry(root_dir=root_dir)
    registry.register(
        load_agent_spec(REPO_ROOT / "examples/control_plane/agent_external_gateway.yaml"),
        actor="test",
    )
    _bind_enrollment(registry=registry, root_dir=root_dir)
    return root_dir


def _submit_request(plan, root_dir: Path) -> AssistantTaskSubmissionRequest:
    return AssistantTaskSubmissionRequest(
        proposalId=plan.proposal_id,
        confirmPlanHash=plan.plan_hash,
        operatorId="operator-local",
        rootDir=str(root_dir),
    )
