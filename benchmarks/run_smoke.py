from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from binliquid.core.llm_ollama import OllamaLLM
from binliquid.core.orchestrator import Orchestrator
from binliquid.core.planner import Planner
from binliquid.experts.code_lite import CodeLiteExpert
from binliquid.experts.plan_lite import PlanLiteExpert
from binliquid.experts.research_lite import ResearchLiteExpert
from binliquid.memory.manager import MemoryManager
from binliquid.memory.persistent_store import PersistentMemoryStore
from binliquid.memory.salience_gate import SalienceGate
from binliquid.router.rule_router import RuleRouter
from binliquid.router.sltc_router import SLTCRouter
from binliquid.runtime.config import RuntimeConfig
from binliquid.telemetry.tracer import Tracer


def run_smoke_benchmark(
    profile: str = "lite",
    mode: str = "both",
    output_path: str | None = None,
    task_limit: int | None = None,
) -> dict[str, Any]:
    selected_modes = _resolve_modes(mode)
    tasks = _load_tasks(
        Path(__file__).resolve().parent / "tasks" / "smoke_tasks.jsonl",
        task_limit=task_limit,
    )

    config = RuntimeConfig.from_profile(profile)
    result: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "profile": profile,
        "mode": mode,
        "results": {},
    }

    for mode_name in selected_modes:
        run_result = _run_mode(tasks=tasks, config=config, mode_name=mode_name)
        result["results"][mode_name] = run_result

    destination = Path(output_path) if output_path else _default_output_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["output_path"] = str(destination)
    return result


def _run_mode(
    tasks: list[dict[str, str]],
    config: RuntimeConfig,
    mode_name: str,
) -> dict[str, Any]:
    answer_llm = OllamaLLM(model_name=config.model_name, temperature=config.answer_temperature)
    planner_llm = OllamaLLM(model_name=config.model_name, temperature=config.planner_temperature)
    planner = Planner(
        planner_llm,
        default_latency_budget_ms=config.latency_budget_ms,
        llm_timeout_ms=config.limits.llm_timeout_ms,
    )
    router, use_router, memory_enabled = _build_mode_runtime(mode_name=mode_name, config=config)

    experts = {
        "code_expert": CodeLiteExpert(),
        "research_expert": ResearchLiteExpert(workspace=Path.cwd()),
        "plan_expert": PlanLiteExpert(),
    }
    tracer = Tracer(debug_mode=False, privacy_mode=True, trace_dir=config.trace_dir)
    memory_manager = _build_memory_manager(config=config, enabled=memory_enabled)

    orchestrator = Orchestrator(
        planner=planner,
        llm=answer_llm,
        router=router,
        experts=experts,
        tracer=tracer,
        config=config,
        memory_manager=memory_manager,
    )

    latencies: list[int] = []
    successes = 0
    fallbacks = 0
    wrong_routes = 0
    route_checks = 0
    expert_calls = 0
    memory_writes = 0
    peak_rss = 0
    process = psutil.Process()

    for task in tasks:
        output = orchestrator.process(task["input"], session_context={}, use_router=use_router)
        latencies.append(int(output.metrics.get("total_latency_ms", 0)))
        if output.final_text.strip():
            successes += 1
        if output.fallback_events:
            fallbacks += 1
        if output.used_path.startswith("expert"):
            expert_calls += 1
        if bool(output.metrics.get("memory_written", False)):
            memory_writes += 1

        if use_router:
            route_checks += 1
            expected = _expected_route(task["task_type"])
            actual = str(output.metrics.get("route_selected_expert", "llm_only"))
            if expected != actual:
                wrong_routes += 1

        peak_rss = max(peak_rss, process.memory_info().rss)

    total_latency_ms = sum(latencies)
    return {
        "task_count": len(tasks),
        "success_rate": round(successes / max(len(tasks), 1), 4),
        "p50_latency_ms": _percentile(latencies, 50),
        "p95_latency_ms": _percentile(latencies, 95),
        "peak_ram_mb": round(peak_rss / (1024 * 1024), 2),
        "fallback_rate": round(fallbacks / max(len(tasks), 1), 4),
        "wrong_route_rate": round(wrong_routes / max(route_checks, 1), 4) if use_router else 0.0,
        "expert_call_rate": round(expert_calls / max(len(tasks), 1), 4),
        "memory_write_rate": round(memory_writes / max(len(tasks), 1), 4),
        "energy_estimate_wh": round(_estimate_energy_wh(total_latency_ms, peak_rss), 5),
        "router_kind": type(router).__name__ if use_router else "None",
    }


def _build_mode_runtime(
    mode_name: str,
    config: RuntimeConfig,
) -> tuple[RuleRouter | SLTCRouter, bool, bool]:
    if mode_name == "A":
        return RuleRouter(confidence_threshold=config.router_confidence_threshold), False, False
    if mode_name == "B":
        return RuleRouter(confidence_threshold=config.router_confidence_threshold), True, False
    if mode_name == "C":
        return (
            SLTCRouter(
                confidence_threshold=config.sltc.confidence_threshold,
                decay=config.sltc.decay,
                spike_threshold=config.sltc.spike_threshold,
            ),
            True,
            False,
        )
    if mode_name == "D":
        return (
            SLTCRouter(
                confidence_threshold=config.sltc.confidence_threshold,
                decay=config.sltc.decay,
                spike_threshold=config.sltc.spike_threshold,
            ),
            True,
            True,
        )
    raise ValueError(f"Unsupported mode: {mode_name}")


def _build_memory_manager(config: RuntimeConfig, enabled: bool) -> MemoryManager:
    store = PersistentMemoryStore(db_path=config.memory.db_path)
    gate = SalienceGate(
        threshold=config.memory.salience_threshold,
        decay=config.memory.salience_decay,
    )
    return MemoryManager(enabled=enabled, store=store, gate=gate, max_rows=config.memory.max_rows)


def _resolve_modes(mode: str) -> list[str]:
    normalized = mode.strip().upper()
    if normalized in {"A", "B", "C", "D"}:
        return [normalized]
    if normalized == "BOTH":
        return ["A", "B"]
    if normalized == "ALL":
        return ["A", "B", "C", "D"]
    raise ValueError("mode must be one of: A, B, C, D, both, all")


def _load_tasks(path: Path, task_limit: int | None = None) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        tasks.append(json.loads(line))
        if task_limit is not None and task_limit > 0 and len(tasks) >= task_limit:
            break
    return tasks


def _expected_route(task_type: str) -> str:
    mapping = {
        "chat": "llm_only",
        "plan": "plan_expert",
        "research": "research_expert",
        "code": "code_expert",
        "mixed": "research_expert",
    }
    return mapping.get(task_type, "llm_only")


def _percentile(values: list[int], percentile: int) -> int:
    if not values:
        return 0
    if len(values) == 1:
        return values[0]

    sorted_values = sorted(values)
    if percentile == 50:
        return int(statistics.median(sorted_values))

    index = int(round((percentile / 100) * (len(sorted_values) - 1)))
    return int(sorted_values[index])


def _estimate_energy_wh(total_latency_ms: int, peak_rss_bytes: int) -> float:
    # Simple system-level estimate for offline smoke runs when hardware power telemetry
    # is unavailable. This is not a final energy benchmark.
    elapsed_h = max(total_latency_ms / 3_600_000, 0.000001)
    rss_gb = peak_rss_bytes / (1024**3)
    assumed_watts = 6.5 + (rss_gb * 1.3)
    return assumed_watts * elapsed_h


def _default_output_path() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("benchmarks") / "results" / f"smoke_{timestamp}.json"


if __name__ == "__main__":
    payload = run_smoke_benchmark(mode="all")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
