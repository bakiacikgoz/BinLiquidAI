from __future__ import annotations

from benchmarks.run_ablation import run_energy_benchmark


def test_energy_payload_contains_v02_schema(monkeypatch) -> None:
    def fake_smoke(**_: object):
        return {
            "output_path": "benchmarks/results/smoke_fake.json",
            "results": {"A": {"energy_estimate_wh": 0.05}},
        }

    class FakeMeasured:
        ok = False
        wh = None
        detail = "powermetrics requires elevated permission"
        confidence = 0.0
        error_reason = "permission_denied"
        notes = "need sudo"

    monkeypatch.setattr("benchmarks.run_ablation.run_smoke_benchmark", fake_smoke)
    monkeypatch.setattr(
        "benchmarks.run_ablation.measure_energy_wh",
        lambda duration_s=6: FakeMeasured(),
    )

    payload = run_energy_benchmark(profile="balanced", energy_mode="measured", task_limit=1)

    assert payload["measurement_mode"] == "measured"
    measured = payload["measured"]
    assert measured["measurement_mode"] == "measured"
    assert measured["tool_name"] == "powermetrics"
    assert "confidence" in measured
    assert "error_reason" in measured
    assert "platform_info" in measured
