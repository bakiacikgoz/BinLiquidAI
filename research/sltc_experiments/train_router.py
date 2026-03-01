from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Any


@dataclass(slots=True)
class TrainResult:
    model_path: str
    metrics_path: str
    report_path: str
    sample_count: int


def train_router_model(
    dataset_path: str | Path,
    output_dir: str | Path,
    seed: int = 42,
) -> dict[str, Any]:
    rng = Random(seed)
    dataset = _load_dataset(dataset_path)
    if not dataset:
        raise ValueError("router dataset is empty")

    by_task: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for item in dataset:
        task_type = str(item.get("task_type", "chat"))
        selected_expert = str(item.get("router_selected_expert", "llm_only"))
        by_task[task_type][selected_expert].append(item)

    model: dict[str, Any] = {
        "seed": seed,
        "task_expert_preferences": {},
        "confidence_bias": {},
    }
    summary_rows: list[dict[str, Any]] = []

    for task_type, expert_map in sorted(by_task.items()):
        scored: list[tuple[str, float, int]] = []
        for expert, rows in expert_map.items():
            success_count = sum(1 for row in rows if bool(row.get("success", False)))
            success_rate = success_count / max(len(rows), 1)
            latency_ms = sum(float(row.get("total_latency_ms", 0)) for row in rows)
            latency_ms = latency_ms / max(len(rows), 1)
            score = success_rate - min(latency_ms / 10_000, 0.5)
            scored.append((expert, score, len(rows)))

        scored.sort(key=lambda item: (item[1], item[2], rng.random()), reverse=True)
        preferred = scored[0][0]
        model["task_expert_preferences"][task_type] = preferred
        model["confidence_bias"][task_type] = round(scored[0][1], 4)

        summary_rows.append(
            {
                "task_type": task_type,
                "preferred_expert": preferred,
                "support": scored[0][2],
                "score": round(scored[0][1], 4),
            }
        )

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = out_dir / "router_model.json"
    metrics_path = out_dir / "train_metrics.json"
    report_path = out_dir / "train_report.md"

    metrics_payload = {
        "sample_count": len(dataset),
        "task_count": len(model["task_expert_preferences"]),
        "summary": summary_rows,
    }

    model_path.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics_path.write_text(
        json.dumps(metrics_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(_build_markdown(metrics_payload), encoding="utf-8")

    return {
        "model_path": str(model_path),
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "sample_count": len(dataset),
    }


def _load_dataset(path: str | Path) -> list[dict[str, Any]]:
    dataset: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        dataset.append(json.loads(line))
    return dataset


def _build_markdown(metrics: dict[str, Any]) -> str:
    lines = [
        "# Router Training Report",
        "",
        f"- Sample count: {metrics.get('sample_count', 0)}",
        f"- Task count: {metrics.get('task_count', 0)}",
        "",
        "| Task | Preferred Expert | Support | Score |",
        "|---|---|---:|---:|",
    ]
    for row in metrics.get("summary", []):
        lines.append(
            f"| {row['task_type']} | {row['preferred_expert']} | "
            f"{row['support']} | {row['score']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train router calibration model from telemetry JSONL."
    )
    parser.add_argument("--dataset", required=True, help="Path to router dataset JSONL")
    parser.add_argument(
        "--output-dir",
        default="research/sltc_experiments/artifacts",
        help="Output directory for model and reports",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    payload = train_router_model(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
