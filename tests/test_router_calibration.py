from __future__ import annotations

import json
from pathlib import Path

from research.sltc_experiments.train_router import calibrate_router_params


def _build_dataset(path: Path) -> None:
    rows: list[dict[str, object]] = []
    task_to_shadow = {
        "chat": "llm_only",
        "code": "code_expert",
        "research": "research_expert",
        "plan": "plan_expert",
        "mixed": "research_expert",
    }
    tasks = ["chat", "code", "research", "plan", "mixed"]
    for idx in range(30):
        task = tasks[idx % len(tasks)]
        rows.append(
            {
                "task_type": task,
                "needs_expert": task != "chat",
                "planner_confidence": 0.85 if task != "chat" else 0.65,
                "latency_budget_ms": 3200 + (idx % 3) * 300,
                "shadow_router_choice": task_to_shadow[task],
                "router_selected_expert": task_to_shadow[task],
                "success": idx % 7 != 0,
                "fallback_activated": idx % 11 == 0,
            }
        )
    path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")


def test_calibrate_router_params_outputs_reproducible_report(tmp_path: Path) -> None:
    dataset = tmp_path / "router_dataset.jsonl"
    _build_dataset(dataset)

    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    first = calibrate_router_params(dataset_path=dataset, output_dir=out_a, seed=13)
    second = calibrate_router_params(dataset_path=dataset, output_dir=out_b, seed=13)

    assert first["best_candidate_id"] == second["best_candidate_id"]
    assert first["best_params"] == second["best_params"]

    report_path = Path(first["report_path"])
    candidates_path = Path(first["candidates_path"])
    markdown_path = Path(first["markdown_path"])

    assert report_path.exists()
    assert candidates_path.exists()
    assert markdown_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["sample_count"] == 30
    assert report["best_holdout_metrics"]["evaluated_samples"] >= 1.0
    assert "latency_penalty_weight" in report["best_params"]
