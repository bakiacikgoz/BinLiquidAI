from typer.testing import CliRunner

from binliquid.cli import app

runner = CliRunner()


def test_doctor_reports_unhealthy_runtime(monkeypatch) -> None:
    def fake_status(model_name: str):
        return {
            "runtime_available": False,
            "ollama_path": None,
            "version": "not-found",
            "daemon_ok": False,
            "model_present": False,
            "model_name": model_name,
        }

    monkeypatch.setattr("binliquid.cli.check_ollama_runtime", fake_status)
    result = runner.invoke(app, ["doctor", "--profile", "lite"])

    assert result.exit_code == 1
    assert '"runtime_available": false' in result.stdout


def test_benchmark_smoke_command(monkeypatch) -> None:
    def fake_benchmark(profile: str, mode: str, output_path: str | None, task_limit: int | None):
        return {
            "profile": profile,
            "mode": mode,
            "output_path": output_path or "benchmarks/results/fake.json",
            "task_limit": task_limit,
            "results": {"A": {"success_rate": 1.0}},
        }

    monkeypatch.setattr("binliquid.cli.run_smoke_benchmark", fake_benchmark)
    result = runner.invoke(app, ["benchmark", "smoke", "--mode", "A", "--profile", "lite"])

    assert result.exit_code == 0
    assert '"mode": "A"' in result.stdout
