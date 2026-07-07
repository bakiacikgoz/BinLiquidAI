from __future__ import annotations

from pathlib import Path

from scripts import run_assistant_governed_tasking_gate as gate


def test_assistant_governed_tasking_gate_passes_when_checks_pass(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        gate,
        "_run",
        lambda command, *, name, required=True, **_: {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 0,
            "status": "pass",
            "reasonCode": "OK",
            "tail": [],
        },
    )

    report = gate.run_assistant_governed_tasking_gate(output_root=tmp_path)

    assert report["status"] == "pass"
    assert report["noShipBlockers"] == []
    assert (tmp_path / "assistant_governed_tasking_gate.json").exists()


def test_assistant_governed_tasking_gate_blocks_failed_required_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fake_run(
        command: list[str],
        *,
        name: str,
        required: bool = True,
        **_: object,
    ) -> dict[str, object]:
        return {
            "name": name,
            "command": command,
            "required": required,
            "returnCode": 1 if name == "python_tasking_tests" else 0,
            "status": "fail" if name == "python_tasking_tests" else "pass",
            "reasonCode": "COMMAND_FAILED" if name == "python_tasking_tests" else "OK",
            "tail": [],
        }

    monkeypatch.setattr(gate, "_run", fake_run)

    report = gate.run_assistant_governed_tasking_gate(output_root=tmp_path)

    assert report["status"] == "fail"
    assert (
        "ASSISTANT_GOVERNED_TASKING_GATE_CHECK_FAILED:python_tasking_tests"
        in report["noShipBlockers"]
    )
