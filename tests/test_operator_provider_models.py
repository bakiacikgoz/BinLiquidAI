import json
import subprocess

from typer.testing import CliRunner

from imperaos.cli import app

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

    monkeypatch.setattr("imperaos.cli.subprocess.run", fake_run)

    result = runner.invoke(
        app,
        ["provider", "models", "--profile", "balanced", "--provider", "ollama", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["contractVersion"] == "operator-panel.assistant-provider-models/v4"
    assert payload["provider"] == "ollama"
    assert payload["providers"][0]["provider"] == "local-ollama"
    assert payload["providers"][0]["conformanceStatus"] == "pass"
    assert any(
        item["id"] == "qwen3.5:4b" and item["installed"] is True
        for item in payload["providers"][0]["models"]
    )


def test_provider_models_includes_native_openai_responses_metadata() -> None:
    result = runner.invoke(
        app,
        ["provider", "models", "--profile", "balanced", "--provider", "all", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    provider = next(
        item for item in payload["providers"] if item["provider"] == "openai-responses-preview"
    )
    assert provider["kind"] == "openai_responses"
    assert provider["nativeAdapterKind"] == "openai_responses"
    assert provider["nativeAdapterStatus"] == "canary_only"
    assert provider["storagePolicy"] == "hash_only/store=false"
    assert provider["serverToolsPolicy"] == "denied"
    assert provider["customToolsPolicy"] == "proposal_only"


def test_provider_models_includes_native_anthropic_messages_metadata() -> None:
    result = runner.invoke(
        app,
        ["provider", "models", "--profile", "balanced", "--provider", "all", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    provider = next(
        item for item in payload["providers"] if item["provider"] == "anthropic-messages-preview"
    )
    assert provider["kind"] == "anthropic_messages"
    assert provider["nativeAdapterKind"] == "anthropic_messages"
    assert provider["nativeAdapterStatus"] == "canary_only"
    assert provider["storagePolicy"] == "hash_only/raw_disabled"
    assert provider["serverToolsPolicy"] == "denied"
    assert provider["clientToolsPolicy"] == "proposal_only"
    assert provider["toolResultLoopPolicy"] == "not_implemented"
    assert provider["liveCanaryStatus"] == "false"


def test_provider_models_reports_unavailable_ollama(monkeypatch) -> None:
    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("ollama")

    monkeypatch.setattr("imperaos.cli.subprocess.run", fake_run)

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


def test_transformers_model_name_does_not_imply_installed_runtime(monkeypatch) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)
    result = runner.invoke(
        app, ["provider", "models", "--profile", "balanced", "--provider", "transformers", "--json"]
    )
    assert result.exit_code == 0, result.stdout
    provider = json.loads(result.stdout)["providers"][0]
    assert provider["models"][0]["configured"] is True
    assert provider["available"] is False
    assert provider["errorCode"] == "TRANSFORMERS_NOT_INSTALLED"


def test_assistant_doctor_requires_setup_without_transformers_package(monkeypatch) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)
    result = runner.invoke(
        app,
        ["assistant", "doctor", "--profile", "balanced", "--provider", "transformers", "--json"],
    )
    assert result.exit_code == 3, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "setup_required"
    assert payload["modelDiscovery"]["selectedDefault"] is None
    assert "TRANSFORMERS_NOT_INSTALLED" in payload["blockingReasons"]
    assert payload["nextActions"]


def test_transformers_requires_the_pytorch_backend(monkeypatch) -> None:
    monkeypatch.setattr(
        "importlib.util.find_spec", lambda name: object() if name == "transformers" else None
    )
    result = runner.invoke(
        app, ["provider", "models", "--profile", "balanced", "--provider", "transformers", "--json"]
    )
    assert result.exit_code == 0, result.stdout
    provider = json.loads(result.stdout)["providers"][0]
    assert provider["available"] is False
    assert provider["errorCode"] == "TORCH_NOT_INSTALLED"


def test_transformers_dependencies_do_not_claim_a_cached_model(monkeypatch) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: object())
    result = runner.invoke(
        app, ["provider", "models", "--profile", "balanced", "--provider", "transformers", "--json"]
    )
    assert result.exit_code == 0, result.stdout
    provider = json.loads(result.stdout)["providers"][0]
    assert provider["available"] is True
    assert provider["models"][0]["installed"] is False
    assert provider["models"][0]["warnings"]
