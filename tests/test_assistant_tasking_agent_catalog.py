from __future__ import annotations

from pathlib import Path

from binliquid.assistant_tasking.agent_catalog import resolve_agent_candidates
from binliquid.control_plane.registry import AgentRegistry, load_agent_spec
from tests.test_external_agent_gateway_v1_1 import _bind_enrollment

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_agent_catalog_requires_enrollment_and_workspace_binding(tmp_path: Path) -> None:
    root_dir = tmp_path / "cp"
    registry = AgentRegistry(root_dir=root_dir)
    registry.register(
        load_agent_spec(REPO_ROOT / "examples/control_plane/agent_external_gateway.yaml"),
        actor="test",
    )
    unenrolled = resolve_agent_candidates(root_dir=root_dir, workspace_id="pilot-workspace")
    assert unenrolled[0].enrolled is False
    assert "ASSISTANT_TASK_UNENROLLED_AGENT_DENIED" in unenrolled[0].blocking_reasons

    _bind_enrollment(registry=registry, root_dir=root_dir)
    enrolled = resolve_agent_candidates(root_dir=root_dir, workspace_id="pilot-workspace")
    assert enrolled[0].enrolled is True
    assert enrolled[0].allowed_surfaces == ("external_gateway",)
