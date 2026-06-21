from __future__ import annotations

from pathlib import Path

from scripts import run_first_run_readiness_gate as gate


def test_first_run_gate_accepts_setup_required_diagnostic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "_run",
        lambda command, *, name, required=True: {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 3,
            "status": "pass",
            "reasonCode": "FIRST_RUN_SETUP_REQUIRED_DIAGNOSTIC",
            "json": {
                "schemaVersion": "setup.first-run/v1",
                "status": "setup_required",
                "blockingReasons": ["ASSISTANT_MODEL_UNAVAILABLE"],
                "nextActions": ["Configure provider"],
            },
            "tail": [],
        },
    )

    report = gate.run_first_run_gate(output_root=tmp_path, profile="enterprise")

    assert report["status"] == "pass"
    assert report["installerFirstRun"] == "pass"
    assert report["conditionalNotes"] == ["ASSISTANT_MODEL_UNAVAILABLE"]
    assert (tmp_path / "first_run_readiness_gate.json").exists()
