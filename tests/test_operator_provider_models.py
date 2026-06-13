import json
import subprocess

from typer.testing import CliRunner

from binliquid.cli import app

runner = CliRunner()


def test_provider_models_lists_ollama_models_without_pulling(monkeypatch) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args[0] == ["ollama", "list"]
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(
            args=["ollama", "list"],
            returncode=0,
            stdout="NAME ID SIZE MODIFIED\nqwen3.5:4b abc 2.0GB 1 hour ago\n",
            stderr="",
        )

    monkeypatch.setattr("binliquid.cli.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        ["provider", "models", "--profile", "balanced", "--provider", "ollama", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["contractVersion"] == "operator-panel.assistant-provider-models/v1"
    assert payload["provider"] == "ollama"
    assert payload["providers"][0]["provider"] == "ollama"
    assert any(
        item["id"] == "qwen3.5:4b" and item["installed"] is True
        for item in payload["providers"][0]["models"]
    )


def test_provider_models_reports_unavailable_ollama(monkeypatch) -> None:
    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("ollama")

    monkeypatch.setattr("binliquid.cli.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        ["provider", "models", "--profile", "balanced", "--provider", "ollama", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    provider = payload["providers"][0]
    assert provider["available"] is False
    assert provider["errorCode"] == "OLLAMA_NOT_INSTALLED"
    assert provider["models"][0]["source"] == "config"
