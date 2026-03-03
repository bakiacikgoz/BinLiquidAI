from typer.testing import CliRunner

from binliquid.cli import app
from binliquid.runtime.config import RuntimeConfig

runner = CliRunner()


def test_doctor_reports_unhealthy_runtime(monkeypatch) -> None:
    def fake_status(**_: object):
        return {
            "selected_provider": "ollama",
            "primary": {
                "daemon_ok": False,
                "model_present": False,
            },
        }

    monkeypatch.setattr("binliquid.cli.check_provider_chain", fake_status)
    result = runner.invoke(app, ["doctor", "--profile", "lite"])

    assert result.exit_code == 3
    assert '"selected_provider": "ollama"' in result.stdout


def test_benchmark_smoke_command(monkeypatch) -> None:
    def fake_benchmark(
        profile: str,
        mode: str,
        suite: str,
        output_path: str | None,
        task_limit: int | None,
        provider: str | None = None,
        fallback_provider: str | None = None,
        model: str | None = None,
        hf_model_id: str | None = None,
    ):
        return {
            "profile": profile,
            "mode": mode,
            "suite": suite,
            "output_path": output_path or "benchmarks/results/fake.json",
            "task_limit": task_limit,
            "provider": provider,
            "fallback_provider": fallback_provider,
            "model": model,
            "hf_model_id": hf_model_id,
            "results": {"A": {"success_rate": 1.0}},
        }

    monkeypatch.setattr("binliquid.cli.run_smoke_benchmark", fake_benchmark)
    result = runner.invoke(app, ["benchmark", "smoke", "--mode", "A", "--profile", "lite"])

    assert result.exit_code == 0
    assert '"mode": "A"' in result.stdout


def test_benchmark_smoke_passes_model_overrides(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_benchmark(
        profile: str,
        mode: str,
        suite: str,
        output_path: str | None,
        task_limit: int | None,
        provider: str | None = None,
        fallback_provider: str | None = None,
        model: str | None = None,
        hf_model_id: str | None = None,
    ):
        captured["provider"] = provider
        captured["fallback_provider"] = fallback_provider
        captured["model"] = model
        captured["hf_model_id"] = hf_model_id
        return {
            "profile": profile,
            "mode": mode,
            "suite": suite,
            "output_path": output_path or "benchmarks/results/fake.json",
            "task_limit": task_limit,
            "results": {"A": {"success_rate": 1.0}},
        }

    monkeypatch.setattr("binliquid.cli.run_smoke_benchmark", fake_benchmark)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "smoke",
            "--mode",
            "A",
            "--profile",
            "lite",
            "--provider",
            "auto",
            "--model",
            "qwen3.5:4b",
            "--hf-model-id",
            "Qwen/Qwen3.5-4B-Instruct",
        ],
    )

    assert result.exit_code == 0
    assert captured["provider"] == "auto"
    assert captured["model"] == "qwen3.5:4b"
    assert captured["hf_model_id"] == "Qwen/Qwen3.5-4B-Instruct"


def test_benchmark_team_command(monkeypatch) -> None:
    def fake_team_benchmark(
        profile: str,
        suite: str,
        spec_path: str,
        task_limit: int | None,
        output_path: str | None,
        deterministic_mock: bool = False,
        provider: str | None = None,
        fallback_provider: str | None = None,
        model: str | None = None,
        hf_model_id: str | None = None,
    ):
        return {
            "profile": profile,
            "suite": suite,
            "spec_path": spec_path,
            "task_limit": task_limit,
            "output_path": output_path or "benchmarks/results/team_fake.json",
            "deterministic_mock": deterministic_mock,
            "provider": provider,
            "fallback_provider": fallback_provider,
            "model": model,
            "hf_model_id": hf_model_id,
            "success_rate": 1.0,
        }

    monkeypatch.setattr("binliquid.cli.run_team_benchmark", fake_team_benchmark)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "team",
            "--profile",
            "lite",
            "--suite",
            "smoke",
            "--spec",
            "team.yaml",
        ],
    )
    assert result.exit_code == 0
    assert '"suite": "smoke"' in result.stdout


def test_benchmark_team_command_passes_deterministic_mock(monkeypatch) -> None:
    captured: dict[str, bool] = {}

    def fake_team_benchmark(
        profile: str,
        suite: str,
        spec_path: str,
        task_limit: int | None,
        output_path: str | None,
        deterministic_mock: bool = False,
        provider: str | None = None,
        fallback_provider: str | None = None,
        model: str | None = None,
        hf_model_id: str | None = None,
    ):
        del profile, suite, spec_path, task_limit, output_path
        del provider, fallback_provider, model, hf_model_id
        captured["deterministic_mock"] = deterministic_mock
        return {"success_rate": 1.0}

    monkeypatch.setattr("binliquid.cli.run_team_benchmark", fake_team_benchmark)
    result = runner.invoke(
        app,
        [
            "benchmark",
            "team",
            "--profile",
            "lite",
            "--suite",
            "smoke",
            "--spec",
            "team.yaml",
            "--deterministic-mock",
        ],
    )
    assert result.exit_code == 0
    assert captured["deterministic_mock"] is True


def test_config_resolve_command(monkeypatch) -> None:
    def fake_resolve(**_: object):
        return RuntimeConfig.from_profile("lite"), {"llm_provider": "profile"}

    monkeypatch.setattr("binliquid.cli.resolve_runtime_config", fake_resolve)
    result = runner.invoke(app, ["config", "resolve", "--profile", "lite", "--json"])

    assert result.exit_code == 0
    assert '"profile": "lite"' in result.stdout


def test_doctor_rejects_conflicting_transformers_model_override() -> None:
    result = runner.invoke(
        app,
        [
            "doctor",
            "--profile",
            "lite",
            "--provider",
            "transformers",
            "--model",
            "qwen3.5:4b",
        ],
    )

    assert result.exit_code == 1
    assert '"status": "invalid_input"' in result.stdout


def test_doctor_rejects_conflicting_ollama_hf_override() -> None:
    result = runner.invoke(
        app,
        [
            "doctor",
            "--profile",
            "lite",
            "--provider",
            "ollama",
            "--hf-model-id",
            "Qwen/Qwen3.5-4B-Instruct",
        ],
    )

    assert result.exit_code == 1
    assert '"status": "invalid_input"' in result.stdout


def test_config_resolve_rejects_conflicting_transformers_model_override() -> None:
    result = runner.invoke(
        app,
        [
            "config",
            "resolve",
            "--profile",
            "lite",
            "--provider",
            "transformers",
            "--model",
            "qwen3.5:4b",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert '"status": "invalid_input"' in result.stdout
