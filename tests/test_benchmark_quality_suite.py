from __future__ import annotations

import json
from pathlib import Path

from benchmarks.run_ablation import run_ablation_benchmark


def test_quality_suite_has_minimum_120_tasks() -> None:
    path = Path("benchmarks/tasks/quality/quality_tasks.jsonl")
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 120
    # sanity: payloads parse as JSON objects
    sample = json.loads(rows[0])
    assert "task_type" in sample


def test_ablation_forwards_quality_suite(monkeypatch, tmp_path: Path) -> None:
    captured = {"suite": None}

    def fake_smoke(**kwargs: object):
        captured["suite"] = kwargs.get("suite")
        out = tmp_path / "out.json"
        payload = {
            "timestamp": "x",
            "profile": "balanced",
            "mode": "all",
            "suite": kwargs.get("suite"),
            "results": {"A": {"success_rate": 1.0}},
            "output_path": str(out),
        }
        out.write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr("benchmarks.run_ablation.run_smoke_benchmark", fake_smoke)
    payload = run_ablation_benchmark(profile="balanced", mode="all", suite="quality")
    assert captured["suite"] == "quality"
    assert payload["suite"] == "quality"
