from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from binliquid.core.llm_ollama import OllamaLLM
from binliquid.core.orchestrator import Orchestrator
from binliquid.core.planner import Planner
from binliquid.experts.code_expert import CodeExpert
from binliquid.experts.memory_plan_expert import MemoryPlanExpert
from binliquid.experts.research_expert import ResearchExpert
from binliquid.governance.runtime import build_governance_runtime
from binliquid.memory.manager import MemoryManager
from binliquid.memory.persistent_store import PersistentMemoryStore
from binliquid.memory.salience_gate import SalienceGate
from binliquid.router.rule_router import RuleRouter
from binliquid.router.sltc_router import SLTCRouter
from binliquid.runtime.config import RuntimeConfig
from binliquid.schemas.models import ExpertName
from binliquid.team.models import TeamSpec
from binliquid.team.supervisor import TeamSupervisor
from binliquid.telemetry.tracer import Tracer


def run_team_benchmark(
    profile: str = "balanced",
    suite: str = "smoke",
    spec_path: str = "team.yaml",
    task_limit: int | None = None,
    output_path: str | None = None,
    provider: str | None = None,
    fallback_provider: str | None = None,
    model: str | None = None,
    hf_model_id: str | None = None,
) -> dict[str, Any]:
    tasks = _load_tasks(_resolve_tasks_path(suite), task_limit=task_limit)
    spec = _load_team_spec(spec_path)

    config = RuntimeConfig.from_profile(profile)
    if provider is not None:
        config = config.model_copy(update={"llm_provider": provider})
    if fallback_provider is not None:
        config = config.model_copy(update={"fallback_provider": fallback_provider})
    if model is not None:
        config = config.model_copy(update={"model_name": model})
    if hf_model_id is not None:
        config = config.model_copy(update={"hf_model_id": hf_model_id})

    orchestrator = _build_orchestrator(config)
    supervisor = TeamSupervisor(orchestrator=orchestrator, config=config)

    completed = 0
    blocked = 0
    failed = 0
    event_count = 0
    handoff_count = 0

    for idx, task in enumerate(tasks, start=1):
        result = supervisor.run(
            spec=spec,
            request=str(task.get("input", "")),
            case_id=f"bench-case-{idx}",
            job_id=f"bench-job-{idx}",
        )
        if result.job.status.value == "completed":
            completed += 1
        elif result.job.status.value == "blocked":
            blocked += 1
        else:
            failed += 1
        event_count += len(result.events)
        handoff_count += len(result.handoffs)

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "profile": profile,
        "suite": suite,
        "spec_path": spec_path,
        "task_count": len(tasks),
        "success_rate": round(completed / max(len(tasks), 1), 4),
        "blocked_rate": round(blocked / max(len(tasks), 1), 4),
        "failed_rate": round(failed / max(len(tasks), 1), 4),
        "avg_event_count": round(event_count / max(len(tasks), 1), 2),
        "avg_handoff_count": round(handoff_count / max(len(tasks), 1), 2),
    }

    destination = Path(output_path) if output_path else _default_output_path(suite)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["output_path"] = str(destination)
    return payload


def _build_orchestrator(config: RuntimeConfig) -> Orchestrator:
    answer_llm = _build_llm(config=config, temperature=config.answer_temperature)
    planner_llm = _build_llm(config=config, temperature=config.planner_temperature)

    planner = Planner(
        planner_llm,
        default_latency_budget_ms=config.latency_budget_ms,
        llm_timeout_ms=config.limits.llm_timeout_ms,
        repair_enabled=config.planner_tuning.repair_enabled,
        repair_max_attempts=config.planner_tuning.repair_max_attempts,
        prompt_variant=config.planner_tuning.prompt_variant,
    )

    router_mode = config.router_mode.lower()
    if config.sltc.router_mode.lower() == "active":
        router_mode = "sltc"
    router = _build_router(config=config, router_mode=router_mode)

    shadow_router = None
    if config.shadow_router_enabled:
        shadow_router = _build_router(config=config, router_mode=config.shadow_router_mode)

    governance_runtime = build_governance_runtime(config)
    experts = {
        ExpertName.CODE.value: CodeExpert(
            workspace=Path.cwd(),
            verify_config=config.code_verify,
            governance_runtime=governance_runtime,
        ),
        ExpertName.RESEARCH.value: ResearchExpert(workspace=Path.cwd()),
        ExpertName.PLAN.value: MemoryPlanExpert(),
    }

    memory_manager = _build_memory_manager(config)
    tracer = Tracer(
        debug_mode=False,
        privacy_mode=True,
        trace_dir=config.trace_dir,
        router_dataset_path=config.router_dataset_path,
        event_redactor=(
            governance_runtime.trace_redact
            if governance_runtime is not None and config.governance.pii_redaction_enabled
            else None
        ),
    )
    return Orchestrator(
        planner=planner,
        llm=answer_llm,
        router=router,
        experts=experts,
        tracer=tracer,
        config=config,
        memory_manager=memory_manager,
        shadow_router=shadow_router,
        governance_runtime=governance_runtime,
    )


def _build_llm(config: RuntimeConfig, temperature: float) -> OllamaLLM:
    return OllamaLLM(
        model_name=config.model_name,
        temperature=temperature,
        provider_name=config.llm_provider,
        fallback_provider=config.fallback_provider,
        fallback_enabled=config.fallback_enabled,
        hf_model_id=config.hf_model_id,
        device=config.device,
    )


def _build_router(config: RuntimeConfig, router_mode: str) -> RuleRouter | SLTCRouter:
    if router_mode == "sltc":
        return SLTCRouter(
            confidence_threshold=config.sltc.confidence_threshold,
            decay=config.sltc.decay,
            spike_threshold=config.sltc.spike_threshold,
            failure_penalty_weight=config.sltc.failure_penalty_weight,
            latency_penalty_weight=config.sltc.latency_penalty_weight,
            need_bonus=config.sltc.need_bonus,
            conf_bonus=config.sltc.conf_bonus,
            task_bias_overrides=config.sltc.task_bias_overrides,
        )
    return RuleRouter(confidence_threshold=config.router_confidence_threshold)


def _build_memory_manager(config: RuntimeConfig) -> MemoryManager:
    store = (
        PersistentMemoryStore(db_path=config.memory.db_path)
        if config.enable_persistent_memory
        else None
    )
    gate = SalienceGate(
        threshold=config.memory.salience_threshold,
        decay=config.memory.salience_decay,
        task_bonus=config.memory.task_bonus,
        expert_bonus=config.memory.expert_bonus,
        spike_reduction=config.memory.spike_reduction,
        keyword_weights=config.memory.keyword_weights,
    )
    return MemoryManager(
        enabled=config.enable_persistent_memory,
        store=store,
        gate=gate,
        max_rows=config.memory.max_rows,
        ttl_days=config.memory_ttl_days,
        rank_salience_weight=config.memory.rank_salience_weight,
        rank_recency_weight=config.memory.rank_recency_weight,
    )


def _load_team_spec(spec_path: str) -> TeamSpec:
    path = Path(spec_path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    elif suffix == ".toml":
        import tomllib

        with path.open("rb") as file_obj:
            payload = tomllib.load(file_obj)
    elif suffix in {".yaml", ".yml"}:
        import yaml  # type: ignore[import-not-found]

        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Unsupported team spec format for benchmark")
    return TeamSpec.model_validate(payload)


def _resolve_tasks_path(suite: str) -> Path:
    normalized = suite.strip().lower()
    if normalized not in {"smoke", "quality"}:
        raise ValueError("suite must be one of: smoke, quality")
    return Path("benchmarks") / "tasks" / "team" / f"{normalized}_tasks.jsonl"


def _load_tasks(path: Path, task_limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    if task_limit is not None:
        return rows[: max(task_limit, 0)]
    return rows


def _default_output_path(suite: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("benchmarks") / "results" / f"team_{suite}_{timestamp}.json"
