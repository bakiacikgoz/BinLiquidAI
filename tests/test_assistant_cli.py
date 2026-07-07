from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app

runner = CliRunner()


def test_assistant_models_exposes_product_contract(monkeypatch) -> None:
    def fake_provider_models_payload(*, profile: str, requested_provider: str) -> dict[str, object]:
        assert profile == "enterprise"
        assert requested_provider == "all"
        return {
            "contractVersion": "operator-panel.assistant-provider-models/v4",
            "profile": profile,
            "providers": [
                {
                    "provider": "local-ollama",
                    "available": True,
                    "models": [{"id": "llama3.1", "label": "llama3.1", "source": "ollama"}],
                    "disabledReason": None,
                    "errorCode": None,
                },
                {
                    "provider": "local-transformers",
                    "available": False,
                    "models": [],
                    "disabledReason": "HF_MODEL_NOT_CONFIGURED",
                    "errorCode": "HF_MODEL_NOT_CONFIGURED",
                },
            ],
        }

    monkeypatch.setattr("binliquid.cli._provider_models_payload", fake_provider_models_payload)

    result = runner.invoke(app, ["assistant", "models", "--profile", "enterprise", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schemaVersion"] == "assistant.provider-models/v1"
    assert payload["profile"] == "enterprise"
    assert payload["providers"][0]["provider"] == "local-ollama"
    assert payload["providers"][0]["status"] == "available"
    assert payload["providers"][1]["status"] == "unavailable"
    assert payload["providers"][1]["blockingReasons"] == ["HF_MODEL_NOT_CONFIGURED"]
    assert payload["selectedDefault"] == {"provider": "local-ollama", "model": "llama3.1"}


def test_assistant_doctor_reports_model_discovery_without_fake_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "binliquid.cli._provider_models_payload",
        lambda *, profile, requested_provider: {
            "profile": profile,
            "providers": [
                {
                    "provider": "local-ollama",
                    "available": False,
                    "models": [],
                    "errorCode": "OLLAMA_NOT_INSTALLED",
                    "disabledReason": None,
                }
            ],
        },
    )

    result = runner.invoke(app, ["assistant", "doctor", "--profile", "enterprise", "--json"])

    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["schemaVersion"] == "assistant.doctor/v1"
    assert payload["status"] == "setup_required"
    assert "ASSISTANT_MODEL_UNAVAILABLE" in payload["blockingReasons"]
    assert payload["previewFallbackAllowed"] is False


def test_assistant_turn_streams_contract_events(tmp_path: Path, monkeypatch) -> None:
    prompt_path = tmp_path / "compiled_prompt.md"
    prompt_path.write_text("Summarize the selected run.", encoding="utf-8")

    def fake_events(**kwargs):
        assert kwargs["profile"] == "enterprise"
        assert kwargs["session_id"] == "session-1"
        assert kwargs["turn_id"] == "turn-1"
        assert kwargs["prompt"] == "Summarize the selected run."
        return [
            {
                "event": "delta",
                "data": {"text": "Done"},
            },
            {
                "event": "final",
                "data": {"finalText": "Done"},
            },
        ]

    monkeypatch.setattr("binliquid.cli._assistant_turn_events", fake_events)

    result = runner.invoke(
        app,
        [
            "assistant",
            "turn",
            "--profile",
            "enterprise",
            "--session-id",
            "session-1",
            "--turn-id",
            "turn-1",
            "--prompt-file",
            str(prompt_path),
            "--stream-json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [event["event"] for event in events] == ["delta", "final"]
    assert all(event["contractVersion"] == "2.0" for event in events)
    assert all(event["assistantTurnId"] == "turn-1" for event in events)
    assert [event["sequence"] for event in events] == [1, 2]


def test_assistant_knowledge_cli_build_search_and_doctor(tmp_path: Path) -> None:
    build_result = runner.invoke(
        app,
        [
            "assistant",
            "knowledge",
            "build",
            "--profile",
            "enterprise",
            "--output-root",
            str(tmp_path),
            "--json",
        ],
    )

    assert build_result.exit_code == 0, build_result.stdout
    build_payload = json.loads(build_result.stdout)
    assert build_payload["schemaVersion"] == "assistant.system-knowledge-manifest/v1"
    assert build_payload["status"] == "ready"
    assert build_payload["sourceCount"] > 0
    assert build_payload["chunkCount"] > 0

    search_result = runner.invoke(
        app,
        [
            "assistant",
            "knowledge",
            "search",
            "--profile",
            "enterprise",
            "--index-root",
            str(tmp_path),
            "--query",
            "AgeisOs sisteminde nasıl bir agent'e görev verebilirim?",
            "--include-context",
            "--json",
        ],
    )
    assert search_result.exit_code == 0, search_result.stdout
    search_payload = json.loads(search_result.stdout)
    assert search_payload["schemaVersion"] == "assistant.system-knowledge-search/v1"
    assert search_payload["status"] == "ready"
    assert search_payload["intent"] == "agent_task"
    assert any(
        hit["path"] == "docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md"
        for hit in search_payload["hits"]
    )
    assert search_payload["context"]["status"] == "available"

    doctor_result = runner.invoke(
        app,
        [
            "assistant",
            "knowledge",
            "doctor",
            "--profile",
            "enterprise",
            "--output-root",
            str(tmp_path),
            "--json",
        ],
    )
    assert doctor_result.exit_code == 0, doctor_result.stdout
    doctor_payload = json.loads(doctor_result.stdout)
    assert doctor_payload["schemaVersion"] == "assistant.system-knowledge-doctor/v1"
    assert doctor_payload["status"] == "ready"
