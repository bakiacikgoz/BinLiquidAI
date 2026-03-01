from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evaluate_router_model(
    dataset_path: str | Path,
    model_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    dataset = _load_dataset(dataset_path)
    model = json.loads(Path(model_path).read_text(encoding="utf-8"))

    if not dataset:
        raise ValueError("router dataset is empty")

    prefs = model.get("task_expert_preferences", {})

    total = 0
    exact_matches = 0
    success_matches = 0
    for row in dataset:
        total += 1
        task = str(row.get("task_type", "chat"))
        predicted = str(prefs.get(task, "llm_only"))
        actual = str(row.get("router_selected_expert", "llm_only"))
        success = bool(row.get("success", False))
        if predicted == actual:
            exact_matches += 1
            if success:
                success_matches += 1

    payload = {
        "sample_count": total,
        "exact_match_rate": round(exact_matches / max(total, 1), 4),
        "success_match_rate": round(success_matches / max(total, 1), 4),
        "task_preferences": prefs,
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "eval_metrics.json"
    report_path = out_dir / "eval_report.md"
    metrics_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    report_path.write_text(_build_markdown(payload), encoding="utf-8")

    payload["metrics_path"] = str(metrics_path)
    payload["report_path"] = str(report_path)
    return payload


def _build_markdown(metrics: dict[str, Any]) -> str:
    lines = [
        "# Router Evaluation Report",
        "",
        f"- Sample count: {metrics.get('sample_count', 0)}",
        f"- Exact match rate: {metrics.get('exact_match_rate', 0)}",
        f"- Success match rate: {metrics.get('success_match_rate', 0)}",
        "",
        "## Task Preferences",
        "",
    ]
    for task, expert in sorted(metrics.get("task_preferences", {}).items()):
        lines.append(f"- {task}: {expert}")
    lines.append("")
    return "\n".join(lines)


def _load_dataset(path: str | Path) -> list[dict[str, Any]]:
    dataset: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        dataset.append(json.loads(line))
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate router calibration model.")
    parser.add_argument("--dataset", required=True, help="Path to router dataset JSONL")
    parser.add_argument("--model", required=True, help="Path to trained router model JSON")
    parser.add_argument(
        "--output-dir",
        default="research/sltc_experiments/artifacts",
        help="Output directory for eval metrics and report",
    )
    args = parser.parse_args()

    payload = evaluate_router_model(
        dataset_path=args.dataset,
        model_path=args.model,
        output_dir=args.output_dir,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
