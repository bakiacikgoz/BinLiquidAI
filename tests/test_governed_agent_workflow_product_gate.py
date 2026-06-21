from __future__ import annotations

from pathlib import Path

from scripts import run_governed_agent_workflow_product_gate as gate


def test_governed_workflow_product_gate_aggregates_smokes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured_commands: dict[str, list[str]] = {}

    def fake_run(command: list[str], *, name: str, required: bool = True):
        captured_commands[name] = command
        return {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 0,
            "status": "pass",
            "reasonCode": "OK",
            "tail": [],
        }

    monkeypatch.setattr(
        gate,
        "_run",
        fake_run,
    )

    report = gate.run_governed_workflow_gate(output_root=tmp_path, profile="enterprise")

    assert report["status"] == "pass"
    assert report["productReadiness"]["governedWorkflow"] == "pass"
    assert report["noShipBlockers"] == []
    assert [check["name"] for check in report["checks"]] == [
        "enterprise_workspace_onboarding",
        "governed_workflow_demo",
        "memory_smoke",
        "external_gateway_smoke",
        "support_bundle_redaction",
    ]
    external_command = captured_commands["external_gateway_smoke"]
    assert "--json" not in external_command
    assert "--output" in external_command
