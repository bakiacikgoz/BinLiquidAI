from __future__ import annotations

from pathlib import Path

from scripts import run_assistant_real_runtime_gate as gate


def test_assistant_gate_is_conditional_with_setup_required_diagnostic(
    tmp_path: Path, monkeypatch
) -> None:
    def fake_run(
        command: list[str],
        *,
        name: str,
        required: bool = True,
        cwd: Path = gate.REPO_ROOT,
    ) -> dict[str, object]:
        if name == "assistant_doctor":
            return {
                "name": name,
                "command": command,
                "required": required,
                "returnCode": 3,
                "status": "conditional",
                "reasonCode": "ASSISTANT_SETUP_REQUIRED_DIAGNOSTIC",
                "json": {
                    "schemaVersion": "assistant.doctor/v1",
                    "status": "setup_required",
                    "previewFallbackAllowed": False,
                    "blockingReasons": ["ASSISTANT_MODEL_UNAVAILABLE"],
                },
                "tail": [],
            }
        return {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 0,
            "status": "pass",
            "reasonCode": "OK",
            "tail": [],
        }

    monkeypatch.setattr(gate, "_run", fake_run)

    report = gate.run_assistant_gate(output_root=tmp_path, profile="enterprise")

    assert report["status"] == "conditional"
    assert report["productReadiness"]["assistant"] == "conditional"
    assert report["conditionalNotes"] == ["assistant_doctor:ASSISTANT_SETUP_REQUIRED_DIAGNOSTIC"]
    assert report["noShipBlockers"] == []
    assert (tmp_path / "assistant_real_runtime_gate.json").exists()


def test_assistant_gate_blocks_preview_fallback(tmp_path: Path, monkeypatch) -> None:
    def fake_run(
        command: list[str],
        *,
        name: str,
        required: bool = True,
        cwd: Path = gate.REPO_ROOT,
    ) -> dict[str, object]:
        if name == "assistant_doctor":
            return {
                "name": name,
                "command": command,
                "required": required,
                "returnCode": 0,
                "status": "pass",
                "reasonCode": "OK",
                "json": {
                    "schemaVersion": "assistant.doctor/v1",
                    "status": "ready",
                    "previewFallbackAllowed": True,
                    "blockingReasons": [],
                },
                "tail": [],
            }
        return {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 0,
            "status": "pass",
            "reasonCode": "OK",
            "tail": [],
        }

    monkeypatch.setattr(gate, "_run", fake_run)

    report = gate.run_assistant_gate(output_root=tmp_path, profile="enterprise")

    assert report["status"] == "fail"
    assert "ASSISTANT_PREVIEW_IN_PRODUCT_MODE" in report["noShipBlockers"]
