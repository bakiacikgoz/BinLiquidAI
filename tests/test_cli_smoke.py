from typer.testing import CliRunner

from binliquid.cli import app

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

    assert result.exit_code == 1
    assert '"selected_provider": "ollama"' in result.stdout


def test_benchmark_smoke_command(monkeypatch) -> None:
    def fake_benchmark(
        profile: str,
        mode: str,
        output_path: str | None,
        task_limit: int | None,
        provider: str | None = None,
        fallback_provider: str | None = None,
    ):
        return {
            "profile": profile,
            "mode": mode,
            "output_path": output_path or "benchmarks/results/fake.json",
            "task_limit": task_limit,
            "provider": provider,
            "fallback_provider": fallback_provider,
            "results": {"A": {"success_rate": 1.0}},
        }

    monkeypatch.setattr("binliquid.cli.run_smoke_benchmark", fake_benchmark)
    result = runner.invoke(app, ["benchmark", "smoke", "--mode", "A", "--profile", "lite"])

    assert result.exit_code == 0
    assert '"mode": "A"' in result.stdout
