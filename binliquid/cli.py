from __future__ import annotations

import json
from pathlib import Path

import typer

from benchmarks.run_smoke import run_smoke_benchmark
from binliquid.core.llm_ollama import OllamaLLM, check_ollama_runtime
from binliquid.core.orchestrator import Orchestrator
from binliquid.core.planner import Planner
from binliquid.experts.code_lite import CodeLiteExpert
from binliquid.experts.plan_lite import PlanLiteExpert
from binliquid.experts.research_lite import ResearchLiteExpert
from binliquid.memory.manager import MemoryManager
from binliquid.memory.persistent_store import PersistentMemoryStore
from binliquid.memory.salience_gate import SalienceGate
from binliquid.memory.session_store import SessionStore
from binliquid.router.rule_router import RuleRouter
from binliquid.router.sltc_router import SLTCRouter
from binliquid.runtime.config import RuntimeConfig
from binliquid.telemetry.tracer import Tracer

app = typer.Typer(help="BinLiquid AI CLI")
benchmark_app = typer.Typer(help="Benchmark commands")
memory_app = typer.Typer(help="Memory commands")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(memory_app, name="memory")


def _build_orchestrator(
    config: RuntimeConfig,
    workspace: Path | None = None,
    router_mode: str | None = None,
) -> Orchestrator:
    workspace_dir = workspace or Path.cwd()
    answer_llm = OllamaLLM(model_name=config.model_name, temperature=config.answer_temperature)
    planner_llm = OllamaLLM(model_name=config.model_name, temperature=config.planner_temperature)

    planner = Planner(
        planner_llm,
        default_latency_budget_ms=config.latency_budget_ms,
        llm_timeout_ms=config.limits.llm_timeout_ms,
    )
    selected_router_mode = (router_mode or config.router_mode).lower()
    router = _build_router(config=config, router_mode=selected_router_mode)
    experts = {
        "code_expert": CodeLiteExpert(),
        "research_expert": ResearchLiteExpert(workspace=workspace_dir),
        "plan_expert": PlanLiteExpert(),
    }
    memory_manager = _build_memory_manager(config)
    tracer = Tracer(
        debug_mode=config.debug_mode,
        privacy_mode=config.privacy_mode,
        trace_dir=config.trace_dir,
    )
    return Orchestrator(
        planner=planner,
        llm=answer_llm,
        router=router,
        experts=experts,
        tracer=tracer,
        config=config,
        memory_manager=memory_manager,
    )


def _build_router(config: RuntimeConfig, router_mode: str) -> RuleRouter | SLTCRouter:
    if router_mode == "sltc":
        return SLTCRouter(
            confidence_threshold=config.sltc.confidence_threshold,
            decay=config.sltc.decay,
            spike_threshold=config.sltc.spike_threshold,
        )
    return RuleRouter(confidence_threshold=config.router_confidence_threshold)


def _build_memory_manager(config: RuntimeConfig) -> MemoryManager:
    store = PersistentMemoryStore(db_path=config.memory.db_path)
    gate = SalienceGate(
        threshold=config.memory.salience_threshold,
        decay=config.memory.salience_decay,
    )
    return MemoryManager(
        enabled=config.enable_persistent_memory,
        store=store,
        gate=gate,
        max_rows=config.memory.max_rows,
    )


@app.command()
def doctor(profile: str = typer.Option("lite", help="Config profile name")) -> None:
    """Runtime and model health check."""
    config = RuntimeConfig.from_profile(profile)
    status = check_ollama_runtime(config.model_name)
    status["profile"] = profile

    typer.echo(json.dumps(status, indent=2, ensure_ascii=False))

    if not status["runtime_available"] or not status["daemon_ok"]:
        raise typer.Exit(code=1)


@app.command()
def chat(
    profile: str = typer.Option("lite", help="Config profile"),
    once: str | None = typer.Option(None, help="Single prompt mode"),
    debug: bool = typer.Option(False, help="Enable debug mode"),
    privacy_off: bool = typer.Option(False, help="Allow persistent debug traces"),
    router_mode: str | None = typer.Option(None, help="Override router mode: rule|sltc"),
) -> None:
    """Interactive chat with orchestrator + router."""
    config = RuntimeConfig.from_profile(profile)
    if debug:
        config = config.model_copy(update={"debug_mode": True})
    if privacy_off:
        config = config.model_copy(update={"privacy_mode": False})

    orchestrator = _build_orchestrator(config, router_mode=router_mode)
    memory = SessionStore()

    def _run_once(user_text: str) -> None:
        context = {"session_summary": memory.summary_text()}
        manager = getattr(orchestrator, "_memory_manager", None)
        if manager is not None:
            snippets = manager.context_snippets(user_text, limit=config.memory.context_top_k)
            if snippets:
                context["memory_hints"] = "\n---\n".join(snippets)
        result = orchestrator.process(user_text, session_context=context, use_router=True)
        memory.add("user", user_text)
        memory.add("assistant", result.final_text)
        typer.echo(result.final_text)

        if config.debug_mode:
            meta = {
                "used_path": result.used_path,
                "fallback_events": result.fallback_events,
                "metrics": result.metrics,
            }
            typer.echo(json.dumps(meta, ensure_ascii=False))

    if once:
        _run_once(once)
        return

    typer.echo("BinLiquid chat başlatıldı. Çıkmak için /exit yazın.")
    while True:
        user_text = typer.prompt("you")
        if user_text.strip().lower() in {"/exit", "exit", "quit", "/quit"}:
            break
        _run_once(user_text)


@benchmark_app.command("smoke")
def benchmark_smoke(
    profile: str = typer.Option("lite", help="Config profile"),
    mode: str = typer.Option("all", help="A|B|C|D|both|all"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    task_limit: int | None = typer.Option(None, help="Limit number of benchmark tasks"),
) -> None:
    """Run smoke benchmark for baseline A/B."""
    result = run_smoke_benchmark(
        profile=profile,
        mode=mode,
        output_path=output,
        task_limit=task_limit,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))


@memory_app.command("stats")
def memory_stats(profile: str = typer.Option("balanced", help="Config profile")) -> None:
    config = RuntimeConfig.from_profile(profile)
    manager = _build_memory_manager(config)
    typer.echo(json.dumps(manager.stats(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
