from __future__ import annotations

import json
from pathlib import Path

from research.sltc_experiments.eval_router import evaluate_router_model
from research.sltc_experiments.train_router import train_router_model


def test_research_training_and_eval_are_reproducible(tmp_path: Path) -> None:
    dataset = tmp_path / "router_dataset.jsonl"
    rows = [
        {
            "task_type": "code",
            "router_selected_expert": "code_expert",
            "success": True,
            "total_latency_ms": 800,
        },
        {
            "task_type": "research",
            "router_selected_expert": "research_expert",
            "success": True,
            "total_latency_ms": 700,
        },
        {
            "task_type": "code",
            "router_selected_expert": "code_expert",
            "success": False,
            "total_latency_ms": 1800,
        },
    ]
    dataset.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    out_dir = tmp_path / "artifacts"
    trained = train_router_model(dataset_path=dataset, output_dir=out_dir, seed=42)

    assert Path(trained["model_path"]).exists()
    assert Path(trained["metrics_path"]).exists()
    assert Path(trained["report_path"]).exists()

    evaluated = evaluate_router_model(
        dataset_path=dataset,
        model_path=trained["model_path"],
        output_dir=out_dir,
    )

    assert 0.0 <= evaluated["exact_match_rate"] <= 1.0
    assert Path(evaluated["metrics_path"]).exists()
    assert Path(evaluated["report_path"]).exists()
