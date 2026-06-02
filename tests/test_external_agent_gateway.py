from __future__ import annotations

import json
from pathlib import Path

from binliquid.control_plane.external_contracts import ExternalActionRequest
from binliquid.control_plane.external_gateway import ExternalAgentGateway
from binliquid.control_plane.registry import AgentRegistry, load_agent_spec
from binliquid.runtime.config import RuntimeConfig


def test_external_gateway_accepts_read_only_request(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    request = _request("external_agent_read_only_request.json")

    response = gateway.submit_action(request)

    assert response.status == "accepted"
    assert response.run_id is not None
    assert response.approval_id is None
    assert response.evidence_ref is not None
    evidence = json.loads((tmp_path / "cp" / response.evidence_ref).read_text(encoding="utf-8"))
    assert evidence["request"]["payloadHash"] == request.payload_hash
    assert "payload" not in evidence["request"]


def test_external_gateway_creates_approval_for_external_write(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    request = _request("external_agent_mutation_requires_approval.json")

    response = gateway.submit_action(request)

    assert response.status == "blocked_pending_approval"
    assert response.approval_id is not None
    assert response.run_id is not None
    run_payload = json.loads((tmp_path / "cp" / "runs" / f"{response.run_id}.json").read_text())
    assert run_payload["run"]["status"] == "approval_pending"
    assert run_payload["run"]["approval_ids"] == [response.approval_id]


def test_external_gateway_denies_destructive_request(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    request = _request("external_agent_denied_destructive.json")

    response = gateway.submit_action(request)

    assert response.status == "denied"
    assert response.reason_code == "RISK_DENIED"
    assert response.run_id is not None


def test_external_gateway_unknown_agent_is_fail_closed(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    request = _request("external_agent_read_only_request.json").model_copy(
        update={"agent_id": "missing-agent"}
    )

    response = gateway.submit_action(request)

    assert response.status == "unknown_agent"
    assert response.reason_code == "UNKNOWN_AGENT"
    assert response.run_id is None


def _gateway(tmp_path: Path) -> ExternalAgentGateway:
    root_dir = tmp_path / "cp"
    config = RuntimeConfig.from_profile("enterprise")
    config.governance.approval_store_path = str(root_dir / "approvals.sqlite")
    registry = AgentRegistry(root_dir=root_dir)
    registry.register(
        load_agent_spec("examples/control_plane/agent_external_gateway.yaml"),
        actor="test",
    )
    return ExternalAgentGateway(config=config, registry=registry, root_dir=root_dir)


def _request(name: str) -> ExternalActionRequest:
    payload = json.loads(
        Path("contracts/control_plane/fixtures").joinpath(name).read_text(encoding="utf-8")
    )
    return ExternalActionRequest.model_validate(payload)
