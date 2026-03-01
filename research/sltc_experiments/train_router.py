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


def calibrate_router_params(
    dataset_path: str | Path,
    output_dir: str | Path,
    *,
    seed: int = 42,
    holdout_ratio: float = 0.2,
) -> dict[str, Any]:
    rng = Random(seed)
    dataset = _load_dataset(dataset_path)
    if len(dataset) < 10:
        raise ValueError("router calibration dataset needs at least 10 rows")

    shuffled = list(dataset)
    rng.shuffle(shuffled)
    split_idx = max(1, int(len(shuffled) * (1 - holdout_ratio)))
    train_rows = shuffled[:split_idx]
    holdout_rows = shuffled[split_idx:]

    candidates = _generate_candidate_params()
    scored_candidates: list[dict[str, Any]] = []
    for idx, candidate in enumerate(candidates):
        train_metrics = _evaluate_candidate(train_rows, candidate)
        holdout_metrics = (
            _evaluate_candidate(holdout_rows, candidate)
            if holdout_rows
            else train_metrics
        )
        scored_candidates.append(
            {
                "candidate_id": idx,
                "params": candidate,
                "train_metrics": train_metrics,
                "holdout_metrics": holdout_metrics,
            }
        )

    scored_candidates.sort(
        key=lambda item: (
            float(item["train_metrics"]["objective_score"]),
            float(item["holdout_metrics"]["objective_score"]),
            -float(item["train_metrics"]["fallback_rate"]),
        ),
        reverse=True,
    )
    best = scored_candidates[0]

    report = {
        "seed": seed,
        "sample_count": len(dataset),
        "train_count": len(train_rows),
        "holdout_count": len(holdout_rows),
        "best_candidate_id": best["candidate_id"],
        "best_params": best["params"],
        "best_train_metrics": best["train_metrics"],
        "best_holdout_metrics": best["holdout_metrics"],
        "top_candidates": scored_candidates[:5],
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = out_dir / "router_calibration_candidates.json"
    report_path = out_dir / "router_calibration_report.json"
    markdown_path = out_dir / "router_calibration_report.md"

    candidates_path.write_text(
        json.dumps(scored_candidates, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(_build_calibration_markdown(report), encoding="utf-8")

    return {
        "seed": seed,
        "sample_count": len(dataset),
        "train_count": len(train_rows),
        "holdout_count": len(holdout_rows),
        "best_candidate_id": best["candidate_id"],
        "best_params": best["params"],
        "candidates_path": str(candidates_path),
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
    }


def _load_dataset(path: str | Path) -> list[dict[str, Any]]:
    dataset: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        dataset.append(json.loads(line))
    return dataset


def _generate_candidate_params() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for decay in (0.82, 0.85, 0.88):
        for spike_threshold in (0.5, 0.55, 0.6):
            for failure_penalty_weight in (0.25, 0.35, 0.45):
                for latency_penalty_weight in (0.08, 0.12, 0.16):
                    candidates.append(
                        {
                            "decay": decay,
                            "spike_threshold": spike_threshold,
                            "failure_penalty_weight": failure_penalty_weight,
                            "latency_penalty_weight": latency_penalty_weight,
                            "need_bonus": 0.12,
                            "conf_bonus": 0.2,
                        }
                    )
    return candidates


def _evaluate_candidate(rows: list[dict[str, Any]], params: dict[str, float]) -> dict[str, float]:
    if not rows:
        return {
            "objective_score": 0.0,
            "agreement_rate": 0.0,
            "success_alignment_rate": 0.0,
            "fallback_rate": 0.0,
            "latency_budget_compliance": 0.0,
            "evaluated_samples": 0.0,
        }
    agreement = 0
    success_alignment = 0
    fallback = 0
    latency_ok = 0
    for row in rows:
        predicted = _predict_router_choice(row=row, params=params)
        target = str(
            row.get("shadow_router_choice")
            or row.get("router_selected_expert", "llm_only")
        )
        if predicted == target:
            agreement += 1
            if bool(row.get("success", False)):
                success_alignment += 1
        if predicted == "llm_only":
            fallback += 1
        budget = int(float(row.get("latency_budget_ms", 3000)))
        if _estimate_latency_ms(predicted, budget) <= budget:
            latency_ok += 1

    total = max(len(rows), 1)
    agreement_rate = agreement / total
    success_alignment_rate = success_alignment / total
    fallback_rate = fallback / total
    latency_budget_compliance = latency_ok / total
    objective_score = (
        (0.45 * agreement_rate)
        + (0.35 * success_alignment_rate)
        + (0.2 * latency_budget_compliance)
        - (0.1 * fallback_rate)
    )
    return {
        "objective_score": round(objective_score, 4),
        "agreement_rate": round(agreement_rate, 4),
        "success_alignment_rate": round(success_alignment_rate, 4),
        "fallback_rate": round(fallback_rate, 4),
        "latency_budget_compliance": round(latency_budget_compliance, 4),
        "evaluated_samples": float(total),
    }


def _predict_router_choice(row: dict[str, Any], params: dict[str, float]) -> str:
    confidence = float(row.get("planner_confidence", row.get("confidence", 0.5)))
    needs_expert = bool(row.get("needs_expert", True))
    task_type = str(row.get("task_type", "chat"))
    latency_budget = int(float(row.get("latency_budget_ms", 3000)))
    failure_flag = bool(row.get("fallback_activated", False))

    if confidence < 0.55:
        return "llm_only"
    if not needs_expert:
        return "llm_only"

    task_bias = {
        "chat": {"llm_only": 0.25},
        "code": {"code_expert": 0.45, "plan_expert": 0.1},
        "research": {"research_expert": 0.45, "plan_expert": 0.1},
        "plan": {"plan_expert": 0.45, "research_expert": 0.1},
        "mixed": {"research_expert": 0.3, "plan_expert": 0.25, "code_expert": 0.2},
    }
    candidate_pool = {"llm_only", "code_expert", "research_expert", "plan_expert"}
    scores: dict[str, float] = {}
    for candidate in sorted(candidate_pool):
        bias = float(task_bias.get(task_type, {}).get(candidate, 0.0))
        need_bonus = float(params["need_bonus"]) if candidate != "llm_only" else 0.0
        conf_bonus = confidence * float(params["conf_bonus"])
        failure_penalty = float(params["failure_penalty_weight"]) if failure_flag else 0.0
        latency_penalty = (
            float(params["latency_penalty_weight"])
            if _estimate_latency_ms(candidate, latency_budget) > latency_budget
            else 0.0
        )
        scores[candidate] = max(
            0.0,
            bias + need_bonus + conf_bonus - failure_penalty - latency_penalty,
        )

    selected = max(scores, key=scores.get)
    if scores[selected] < float(params["spike_threshold"]):
        return "llm_only"
    return selected


def _estimate_latency_ms(selected_expert: str, budget_ms: int) -> int:
    table = {
        "llm_only": int(budget_ms * 0.7),
        "code_expert": int(budget_ms * 0.95),
        "research_expert": int(budget_ms * 0.9),
        "plan_expert": int(budget_ms * 0.8),
    }
    return max(100, table.get(selected_expert, budget_ms))


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


def _build_calibration_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Router Calibration Report",
        "",
        f"- Seed: {report.get('seed')}",
        f"- Samples: {report.get('sample_count')}",
        f"- Train/Holdout: {report.get('train_count')}/{report.get('holdout_count')}",
        f"- Best candidate: {report.get('best_candidate_id')}",
        "",
        "## Best Params",
        "",
        f"```json\n{json.dumps(report.get('best_params', {}), indent=2, ensure_ascii=False)}\n```",
        "",
        "## Best Metrics",
        "",
        (
            "```json\n"
            f"{json.dumps(report.get('best_holdout_metrics', {}), indent=2, ensure_ascii=False)}\n"
            "```"
        ),
        "",
    ]
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
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run calibration sweep and report generation",
    )
    args = parser.parse_args()

    if args.calibrate:
        payload = calibrate_router_params(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    else:
        payload = train_router_model(
            dataset_path=args.dataset,
            output_dir=args.output_dir,
            seed=args.seed,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
