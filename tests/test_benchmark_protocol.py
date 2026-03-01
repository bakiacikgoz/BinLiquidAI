from __future__ import annotations

from pathlib import Path

from benchmarks.run_ablation import run_ablation_benchmark, run_energy_benchmark


def test_run_ablation_writes_json_and_report(monkeypatch, tmp_path: Path) -> None:
    def fake_smoke(**_: object):
        out = tmp_path / "smoke.json"
        out.write_text(
            '{"timestamp":"x","profile":"lite","mode":"A","results":{"A":{"success_rate":1.0}}}',
            encoding="utf-8",
        )
        return {
            "timestamp": "x",
            "profile": "lite",
            "mode": "A",
            "results": {"A": {"success_rate": 1.0}},
            "output_path": str(out),
        }

    monkeypatch.setattr("benchmarks.run_ablation.run_smoke_benchmark", fake_smoke)

    payload = run_ablation_benchmark(profile="lite", mode="A")

    assert Path(payload["output_path"]).exists()
    assert Path(payload["report_path"]).exists()


def test_run_energy_measured_mode_returns_deterministic_payload(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_smoke(**_: object):
        return {
            "output_path": str(tmp_path / "smoke.json"),
            "results": {"A": {"energy_estimate_wh": 0.0123}},
        }

    class FakeMeasured:
        ok = False
        wh = None
        detail = "powermetrics requires elevated permission"

    monkeypatch.setattr("benchmarks.run_ablation.run_smoke_benchmark", fake_smoke)
    monkeypatch.setattr(
        "benchmarks.run_ablation.measure_energy_wh",
        lambda duration_s=6: FakeMeasured(),
    )

    payload = run_energy_benchmark(profile="lite", energy_mode="measured")

    assert payload["energy_mode"] == "measured"
    assert payload["measured"]["detail"] == "powermetrics requires elevated permission"
