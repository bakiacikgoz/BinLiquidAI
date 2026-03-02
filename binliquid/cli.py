from __future__ import annotations

import hashlib
import json
from pathlib import Path

import typer

from benchmarks.run_ablation import run_ablation_benchmark, run_energy_benchmark
from benchmarks.run_smoke import run_smoke_benchmark
from binliquid.core.llm_ollama import OllamaLLM, check_provider_chain
from binliquid.core.orchestrator import Orchestrator
from binliquid.core.planner import Planner
from binliquid.experts.code_expert import CodeExpert
from binliquid.experts.memory_plan_expert import MemoryPlanExpert
from binliquid.experts.research_expert import ResearchExpert
from binliquid.governance.runtime import (
    GovernanceRuntime,
    build_governance_runtime,
    governance_startup_abort,
)
from binliquid.memory.manager import MemoryManager
from binliquid.memory.persistent_store import PersistentMemoryStore
from binliquid.memory.salience_gate import SalienceGate
from binliquid.memory.session_store import SessionStore
from binliquid.router.rule_router import RuleRouter
from binliquid.router.sltc_router import SLTCRouter
from binliquid.runtime.config import RuntimeConfig, redact_config_payload, resolve_runtime_config
from binliquid.schemas.models import ExpertName
from binliquid.telemetry.artifacts_writer import ensure_artifact_scaffold, write_artifact
from binliquid.telemetry.tracer import Tracer
from research.sltc_experiments.eval_router import evaluate_router_model
from research.sltc_experiments.train_router import calibrate_router_params, train_router_model

app = typer.Typer(help="BinLiquidAI CLI")
benchmark_app = typer.Typer(help="Benchmark commands")
memory_app = typer.Typer(help="Memory commands")
research_app = typer.Typer(help="Research commands")
config_app = typer.Typer(help="Config commands")
approval_app = typer.Typer(help="Governance approval commands")
operator_app = typer.Typer(help="Operator panel commands")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(memory_app, name="memory")
app.add_typer(research_app, name="research")
app.add_typer(config_app, name="config")
app.add_typer(approval_app, name="approval")
app.add_typer(operator_app, name="operator")


def _is_realtime_candidate(user_text: str) -> bool:
    is_candidate, _reason = _realtime_candidate_reason(user_text)
    return is_candidate


def _realtime_candidate_reason(user_text: str) -> tuple[bool, str]:
    text = user_text.strip().lower()
    if not text:
        return False, "empty"

    greetings = {
        "selam",
        "merhaba",
        "hey",
        "hi",
        "hello",
        "nasılsın",
        "naber",
        "günaydın",
        "iyi akşamlar",
    }
    if text in greetings:
        return True, "greeting"

    if len(text) > 64:
        return False, "too_long_chars"
    if len(text.split()) > 10:
        return False, "too_long_words"

    heavy_tokens = {
        "kod",
        "python",
        "test",
        "debug",
        "araştır",
        "research",
        "özet",
        "plan",
        "adım",
        "tool",
        "benchmark",
        "lint",
        "diff",
    }
    if any(token in text for token in heavy_tokens):
        return False, "heavy_token_detected"
    return True, "short_message"


def _build_llm(
    config: RuntimeConfig,
    *,
    temperature: float,
    provider_name: str | None = None,
    fallback_provider: str | None = None,
) -> OllamaLLM:
    return OllamaLLM(
        model_name=config.model_name,
        temperature=temperature,
        provider_name=(provider_name or config.llm_provider),
        fallback_provider=(fallback_provider or config.fallback_provider),
        fallback_enabled=config.fallback_enabled,
        hf_model_id=config.hf_model_id,
        device=config.device,
    )


def _build_orchestrator(
    config: RuntimeConfig,
    workspace: Path | None = None,
    router_mode: str | None = None,
    shadow_router_mode: str | None = None,
    shadow_router_enabled: bool | None = None,
    provider_name: str | None = None,
    fallback_provider: str | None = None,
) -> Orchestrator:
    workspace_dir = workspace or Path.cwd()
    answer_llm = _build_llm(
        config=config,
        temperature=config.answer_temperature,
        provider_name=provider_name,
        fallback_provider=fallback_provider,
    )
    planner_llm = _build_llm(
        config=config,
        temperature=config.planner_temperature,
        provider_name=provider_name,
        fallback_provider=fallback_provider,
    )

    planner = Planner(
        planner_llm,
        default_latency_budget_ms=config.latency_budget_ms,
        llm_timeout_ms=config.limits.llm_timeout_ms,
        repair_enabled=config.planner_tuning.repair_enabled,
        repair_max_attempts=config.planner_tuning.repair_max_attempts,
        prompt_variant=config.planner_tuning.prompt_variant,
    )
    selected_router_mode = (router_mode or config.router_mode).lower()
    sltc_mode = config.sltc.router_mode.lower()
    if sltc_mode == "active":
        selected_router_mode = "sltc"
    if sltc_mode == "off" and selected_router_mode == "sltc":
        selected_router_mode = "rule"
    router = _build_router(config=config, router_mode=selected_router_mode)
    effective_shadow_enabled = (
        config.shadow_router_enabled
        if shadow_router_enabled is None
        else shadow_router_enabled
    )
    if sltc_mode == "shadow":
        effective_shadow_enabled = True
    if sltc_mode == "off":
        effective_shadow_enabled = False
    shadow_router = None
    if effective_shadow_enabled:
        selected_shadow_mode = (shadow_router_mode or config.shadow_router_mode).lower()
        shadow_router = _build_router(config=config, router_mode=selected_shadow_mode)
    governance_runtime = _build_governance_runtime(config)
    experts = {
        ExpertName.CODE.value: CodeExpert(
            workspace=workspace_dir,
            verify_config=config.code_verify,
            governance_runtime=governance_runtime,
        ),
        ExpertName.RESEARCH.value: ResearchExpert(workspace=workspace_dir),
        ExpertName.PLAN.value: MemoryPlanExpert(),
    }
    memory_manager = _build_memory_manager(config)
    tracer = Tracer(
        debug_mode=config.debug_mode,
        privacy_mode=config.privacy_mode,
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


def _build_governance_runtime(config: RuntimeConfig) -> GovernanceRuntime | None:
    runtime = build_governance_runtime(config)
    return runtime


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


@config_app.command("resolve")
def config_resolve(
    profile: str = typer.Option("balanced", help="Config profile"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    cli_overrides = {
        "llm_provider": provider,
        "fallback_provider": fallback_provider,
    }
    resolved, source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=cli_overrides,
    )
    payload = {
        "profile": profile,
        "resolved": redact_config_payload(resolved.model_dump(mode="python")),
        "source_map": source_map,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        typer.echo(f"profile={profile}")
        typer.echo(f"router_mode={resolved.router_mode}")
        typer.echo(f"shadow_router_enabled={resolved.shadow_router_enabled}")
        typer.echo(f"shadow_router_mode={resolved.shadow_router_mode}")


@app.command()
def doctor(profile: str = typer.Option("lite", help="Config profile name")) -> None:
    """Runtime and provider health check."""
    ensure_artifact_scaffold()
    config = RuntimeConfig.from_profile(profile)
    status = check_provider_chain(
        model_name=config.model_name,
        provider_name=config.llm_provider,
        fallback_provider=config.fallback_provider,
        fallback_enabled=config.fallback_enabled,
        hf_model_id=config.hf_model_id,
        device=config.device,
    )
    status["profile"] = profile

    typer.echo(json.dumps(status, indent=2, ensure_ascii=False))
    write_artifact(
        "status",
        {
            "profile": profile,
            "selected_provider": status.get("selected_provider"),
            "primary": status.get("primary", {}),
            "secondary": status.get("secondary", {}),
        },
    )

    primary = status.get("primary", {})
    selected = str(status.get("selected_provider", ""))
    if selected == "ollama":
        daemon_ok = bool(primary.get("daemon_ok", False))
        model_present = bool(primary.get("model_present", False))
        if not (daemon_ok and model_present):
            raise typer.Exit(code=1)


@app.command()
def chat(
    profile: str = typer.Option("lite", help="Config profile"),
    once: str | None = typer.Option(None, help="Single prompt mode"),
    debug: bool = typer.Option(False, help="Enable debug mode"),
    privacy_off: bool = typer.Option(False, help="Allow persistent debug traces"),
    router_mode: str | None = typer.Option(None, help="Override router mode: rule|sltc"),
    provider: str | None = typer.Option(None, help="Override provider: auto|ollama|transformers"),
    fallback_provider: str | None = typer.Option(
        None,
        help="Override fallback provider: transformers|ollama",
    ),
    session_id: str | None = typer.Option(None, help="Optional deterministic session id"),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream realtime tokens when fast path is used.",
    ),
    fast_path: bool = typer.Option(
        True,
        "--fast-path/--no-fast-path",
        help="Use single-call realtime path for short chat inputs.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit single JSON payload."),
    json_stream: bool = typer.Option(
        False,
        "--json-stream",
        help="Emit line-delimited JSON events.",
    ),
    stdio_json: bool = typer.Option(
        False,
        "--stdio-json",
        help="Alias for --json-stream with IPC-friendly events.",
    ),
) -> None:
    """Interactive chat with orchestrator + router."""
    ensure_artifact_scaffold()
    config, _source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides={
            "llm_provider": provider,
            "fallback_provider": fallback_provider,
        },
    )
    if debug:
        config = config.model_copy(update={"debug_mode": True})
    if privacy_off:
        config = config.model_copy(update={"privacy_mode": False})

    orchestrator = _build_orchestrator(
        config,
        router_mode=router_mode,
        provider_name=provider,
        fallback_provider=fallback_provider,
    )
    startup_error = governance_startup_abort(
        config,
        getattr(orchestrator, "governance_runtime", None),
    )
    if startup_error:
        typer.echo(f"POLICY_UNAVAILABLE: {startup_error}")
        raise typer.Exit(code=2)
    memory = SessionStore()
    stream_json = json_stream or stdio_json
    use_json = json_output or stream_json

    def _emit_json_event(event: str, data: dict[str, object]) -> None:
        typer.echo(json.dumps({"event": event, "data": data}, ensure_ascii=False))

    def _emit_trace_events(result_trace_id: str) -> None:
        stage_to_event = {
            "request_received": "status",
            "planner_output": "status",
            "router_decision": "router_decision",
            "router_shadow_decision": "router_decision",
            "policy_decision": "policy_decision",
            "approval_pending": "approval_pending",
            "expert_start": "expert_start",
            "expert_call": "expert_end",
            "memory_write_decision": "status",
            "audit_artifact": "audit_artifact",
            "final_response": "final",
        }
        for event in orchestrator.trace_events(result_trace_id):
            stage = str(event.get("stage", "status"))
            _emit_json_event(
                stage_to_event.get(stage, "status"),
                {
                    "stage": stage,
                    "request_id": event.get("request_id"),
                    "data": event.get("data", {}),
                },
            )

    def _run_once(user_text: str) -> None:
        sid = session_id or "session-default"
        context = {
            "session_summary": memory.summary_text(),
            "session_id": sid,
        }
        manager = getattr(orchestrator, "_memory_manager", None)
        if manager is not None:
            snippets = manager.context_snippets(user_text, limit=config.memory.context_top_k)
            if snippets:
                context["memory_hints"] = "\n---\n".join(snippets)

        use_realtime, candidate_reason = _realtime_candidate_reason(user_text)
        use_realtime = fast_path and use_realtime
        if stream_json:
            _emit_json_event(
                "status",
                {
                    "phase": "start",
                    "session_id": sid,
                    "realtime_candidate": use_realtime,
                    "candidate_reason": candidate_reason,
                },
            )
        if use_realtime:
            if stream:
                result = orchestrator.process_fast_chat(
                    user_text,
                    session_context=context,
                    stream=True,
                    candidate_reason=candidate_reason,
                    on_token=(
                        (lambda token: _emit_json_event("token", {"text": token}))
                        if stream_json
                        else (lambda token: print(token, end="", flush=True))
                    ),
                )
                if not stream_json:
                    print()
                if result.used_path != "llm_stream_fast" and not use_json:
                    typer.echo(result.final_text)
            else:
                result = orchestrator.process_fast_chat(
                    user_text,
                    session_context=context,
                    stream=False,
                    candidate_reason=candidate_reason,
                )
                if not use_json:
                    typer.echo(result.final_text)
        else:
            result = orchestrator.process(user_text, session_context=context, use_router=True)
            if not use_json:
                typer.echo(result.final_text)

        memory.add("user", user_text)
        memory.add("assistant", result.final_text)

        if use_json and json_output and not stream_json:
            payload = {
                "trace_id": result.trace_id,
                "final_text": result.final_text,
                "used_path": result.used_path,
                "fallback_events": result.fallback_events,
                "metrics": result.metrics,
                "trace_events": orchestrator.trace_events(result.trace_id),
            }
            typer.echo(json.dumps(payload, ensure_ascii=False))
        elif stream_json:
            _emit_trace_events(result.trace_id)
            _emit_json_event(
                "final",
                {
                    "trace_id": result.trace_id,
                    "final_text": result.final_text,
                    "used_path": result.used_path,
                    "fallback_events": result.fallback_events,
                    "metrics": result.metrics,
                },
            )
        elif config.debug_mode:
            meta = {
                "used_path": result.used_path,
                "fallback_events": result.fallback_events,
                "metrics": result.metrics,
                "realtime_candidate": use_realtime,
                "fast_path_candidate_reason": candidate_reason,
            }
            typer.echo(json.dumps(meta, ensure_ascii=False))

        write_artifact(
            "router_shadow_summary",
            {
                "trace_id": result.trace_id,
                "router_shadow_enabled": result.metrics.get("router_shadow_enabled"),
                "router_shadow_agreement": result.metrics.get("router_shadow_agreement"),
                "active_router_choice": result.metrics.get("active_router_choice"),
                "shadow_router_choice": result.metrics.get("shadow_router_choice"),
                "fast_path_regret_flag": result.metrics.get("fast_path_regret_flag"),
                "followup_correction_rate": result.metrics.get("followup_correction_rate"),
            },
        )
        write_artifact(
            "governance_summary",
            {
                "trace_id": result.trace_id,
                "governance_action": result.metrics.get("governance_action"),
                "governance_reason_code": result.metrics.get("governance_reason_code"),
                "policy_hash": result.metrics.get("policy_hash"),
                "approval_id": result.metrics.get("approval_id"),
                "audit_artifact_path": result.metrics.get("audit_artifact_path"),
            },
        )

    if once:
        _run_once(once)
        return

    typer.echo("BinLiquid chat başlatıldı. Çıkmak için /exit yazın.")
    while True:
        user_text = typer.prompt("you")
        if user_text.strip().lower() in {"/exit", "exit", "quit", "/quit"}:
            break
        _run_once(user_text)


def _hash_payload(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@approval_app.command("pending")
def approval_pending(
    profile: str = typer.Option("balanced", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runtime = _build_governance_runtime(config)
    if runtime is None:
        typer.echo("Governance disabled.")
        raise typer.Exit(code=1)
    tickets = [item.model_dump(mode="json") for item in runtime.approval_store.list_pending()]
    if json_output:
        typer.echo(json.dumps({"pending": tickets}, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"pending_count={len(tickets)}")
        for item in tickets:
            typer.echo(
                f"- {item['approval_id']} status={item['status']} "
                f"expires_at={item['expires_at']} run_id={item['run_id']}"
            )


@approval_app.command("decide")
def approval_decide(
    approval_id: str = typer.Option(..., "--id", help="Approval ticket id"),
    approve: bool = typer.Option(False, "--approve", help="Approve ticket"),
    reject: bool = typer.Option(False, "--reject", help="Reject ticket"),
    actor: str = typer.Option(..., "--actor", help="Actor identity"),
    reason: str | None = typer.Option(None, "--reason", help="Decision note"),
    profile: str = typer.Option("balanced", help="Config profile"),
) -> None:
    if approve == reject:
        typer.echo("Use exactly one of --approve or --reject.")
        raise typer.Exit(code=2)

    config = RuntimeConfig.from_profile(profile)
    runtime = _build_governance_runtime(config)
    if runtime is None:
        typer.echo("Governance disabled.")
        raise typer.Exit(code=1)

    result = runtime.decide_approval(
        approval_id=approval_id,
        approve=approve,
        actor=actor,
        reason=reason,
    )
    payload = {
        "approval_id": approval_id,
        "error_code": result.error_code,
        "ticket": result.ticket.model_dump(mode="json") if result.ticket else None,
    }
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    if result.error_code:
        raise typer.Exit(code=1)


@approval_app.command("execute")
def approval_execute(
    approval_id: str = typer.Option(..., "--id", help="Approval ticket id"),
    actor: str = typer.Option(..., "--actor", help="Execution actor identity"),
    profile: str = typer.Option("balanced", help="Config profile"),
) -> None:
    ensure_artifact_scaffold()
    config = RuntimeConfig.from_profile(profile)
    runtime = _build_governance_runtime(config)
    if runtime is None:
        typer.echo("Governance disabled.")
        raise typer.Exit(code=1)

    startup_error = governance_startup_abort(config, runtime)
    if startup_error:
        typer.echo(f"POLICY_UNAVAILABLE: {startup_error}")
        raise typer.Exit(code=2)

    ticket = runtime.approval_store.get(approval_id)
    if ticket is None:
        typer.echo(json.dumps({"error_code": "APPROVAL_NOT_FOUND", "approval_id": approval_id}))
        raise typer.Exit(code=1)
    if ticket.status.value == "expired":
        typer.echo(json.dumps({"error_code": "APPROVAL_EXPIRED", "approval_id": approval_id}))
        raise typer.Exit(code=1)
    if ticket.execution_status.value == "executed":
        typer.echo(json.dumps({"error_code": "REPLAY_BLOCKED", "approval_id": approval_id}))
        raise typer.Exit(code=1)

    snapshot_hash = _hash_payload(ticket.snapshot)
    if snapshot_hash != ticket.snapshot_hash:
        typer.echo(json.dumps({"error_code": "REPLAY_BLOCKED", "approval_id": approval_id}))
        raise typer.Exit(code=1)

    kind = str(ticket.snapshot.get("kind", ""))
    if kind == "task":
        request_hash = _hash_payload(
            {
                "task_type": ticket.snapshot.get("task_type"),
                "user_input": ticket.snapshot.get("user_input"),
            }
        )
    else:
        request_hash = _hash_payload(ticket.snapshot.get("normalized", []))
    if request_hash != ticket.request_hash:
        typer.echo(json.dumps({"error_code": "REPLAY_BLOCKED", "approval_id": approval_id}))
        raise typer.Exit(code=1)

    if kind != "task":
        fail = runtime.approval_store.mark_execution_failed(
            approval_id=approval_id,
            error_code="UNSUPPORTED_SNAPSHOT_KIND",
        )
        typer.echo(
            json.dumps(
                {
                    "approval_id": approval_id,
                    "error_code": "UNSUPPORTED_SNAPSHOT_KIND",
                    "ticket": fail.ticket.model_dump(mode="json") if fail.ticket else None,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    orchestrator = _build_orchestrator(config)
    context = {
        "session_id": f"approval-{approval_id[:8]}",
        "governance_approval_id": approval_id,
    }
    result = orchestrator.process(
        str(ticket.snapshot.get("user_input", "")),
        session_context=context,
        use_router=True,
    )
    output = {
        "approval_id": approval_id,
        "actor": actor,
        "execution_used_path": result.used_path,
        "trace_id": result.trace_id,
        "fallback_events": result.fallback_events,
        "metrics": result.metrics,
    }
    if result.used_path in {"governance_pending", "governance_blocked"}:
        runtime.approval_store.mark_execution_failed(
            approval_id=approval_id,
            error_code="EXECUTION_FAILED",
        )
        output["error_code"] = "EXECUTION_FAILED"
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
        raise typer.Exit(code=1)

    decision = runtime.execute_approval(approval_id=approval_id)
    if decision.error_code:
        output["error_code"] = decision.error_code
        output["ticket"] = decision.ticket.model_dump(mode="json") if decision.ticket else None
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
        raise typer.Exit(code=1)

    output["ticket"] = decision.ticket.model_dump(mode="json") if decision.ticket else None
    typer.echo(json.dumps(output, ensure_ascii=False, indent=2))


@operator_app.command("panel")
def operator_panel(
    profile: str = typer.Option("balanced", help="Config profile"),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Reserved for future trace tail",
    ),
) -> None:
    _ = stream
    config = RuntimeConfig.from_profile(profile)
    runtime = _build_governance_runtime(config)
    startup_error = governance_startup_abort(config, runtime)
    if startup_error:
        typer.echo(f"[blocked-mode] POLICY_UNAVAILABLE: {startup_error}")
        typer.echo("Commands available: /pending, /approve <id>, /reject <id>, /exit")
    else:
        typer.echo("Operator panel started. Commands: /pending, /approve <id>, /reject <id>, /exit")

    if runtime is None:
        typer.echo("Governance disabled; operator panel requires governance.")
        raise typer.Exit(code=1)

    while True:
        line = typer.prompt("operator")
        text = line.strip()
        if text in {"/exit", "exit", "quit", "/quit"}:
            break
        if text == "/pending":
            pending = runtime.approval_store.list_pending()
            typer.echo(
                json.dumps(
                    {"pending": [item.model_dump(mode="json") for item in pending]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            continue
        if text.startswith("/approve "):
            approval_id = text.split(maxsplit=1)[1]
            result = runtime.decide_approval(
                approval_id=approval_id,
                approve=True,
                actor="operator-panel",
                reason="approved from panel",
            )
            typer.echo(
                json.dumps(
                    {
                        "error_code": result.error_code,
                        "ticket": result.ticket.model_dump(mode="json") if result.ticket else None,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            continue
        if text.startswith("/reject "):
            approval_id = text.split(maxsplit=1)[1]
            result = runtime.decide_approval(
                approval_id=approval_id,
                approve=False,
                actor="operator-panel",
                reason="rejected from panel",
            )
            typer.echo(
                json.dumps(
                    {
                        "error_code": result.error_code,
                        "ticket": result.ticket.model_dump(mode="json") if result.ticket else None,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            continue
        typer.echo("Unknown command. Use /pending, /approve <id>, /reject <id>, /exit.")


@benchmark_app.command("smoke")
def benchmark_smoke(
    profile: str = typer.Option("lite", help="Config profile"),
    mode: str = typer.Option("all", help="A|B|C|D|both|all"),
    suite: str = typer.Option("smoke", help="smoke|quality"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    task_limit: int | None = typer.Option(None, help="Limit number of benchmark tasks"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
) -> None:
    ensure_artifact_scaffold()
    result = run_smoke_benchmark(
        profile=profile,
        mode=mode,
        suite=suite,
        output_path=output,
        task_limit=task_limit,
        provider=provider,
        fallback_provider=fallback_provider,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    write_artifact("benchmark_summary", {"kind": "smoke", "result": result})


@benchmark_app.command("ablation")
def benchmark_ablation(
    profile: str = typer.Option("balanced", help="Config profile"),
    mode: str = typer.Option("all", help="A|B|C|D|both|all"),
    suite: str = typer.Option("smoke", help="smoke|quality"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    report: str | None = typer.Option(None, help="Output markdown report path"),
    task_limit: int | None = typer.Option(None, help="Limit number of benchmark tasks"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
) -> None:
    ensure_artifact_scaffold()
    result = run_ablation_benchmark(
        profile=profile,
        mode=mode,
        output_path=output,
        report_path=report,
        task_limit=task_limit,
        suite=suite,
        provider=provider,
        fallback_provider=fallback_provider,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    write_artifact("benchmark_summary", {"kind": "ablation", "result": result})


@benchmark_app.command("energy")
def benchmark_energy(
    profile: str = typer.Option("balanced", help="Config profile"),
    energy_mode: str = typer.Option("measured", help="measured|estimated"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    task_limit: int | None = typer.Option(2, help="Limit number of benchmark tasks"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
) -> None:
    ensure_artifact_scaffold()
    result = run_energy_benchmark(
        profile=profile,
        energy_mode=energy_mode,
        task_limit=task_limit,
        output_path=output,
        provider=provider,
        fallback_provider=fallback_provider,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    write_artifact("benchmark_summary", {"kind": "energy", "result": result})


@memory_app.command("stats")
def memory_stats(profile: str = typer.Option("balanced", help="Config profile")) -> None:
    ensure_artifact_scaffold()
    config = RuntimeConfig.from_profile(profile)
    manager = _build_memory_manager(config)
    typer.echo(json.dumps(manager.stats(), indent=2, ensure_ascii=False))


@research_app.command("train-router")
def research_train_router(
    dataset: str = typer.Option(
        ".binliquid/research/router_dataset.jsonl",
        help="Dataset JSONL path",
    ),
    output_dir: str = typer.Option(
        "research/sltc_experiments/artifacts",
        help="Output directory",
    ),
    seed: int = typer.Option(42, help="Random seed"),
) -> None:
    ensure_artifact_scaffold()
    payload = train_router_model(dataset_path=dataset, output_dir=output_dir, seed=seed)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    write_artifact("research_summary", {"kind": "train_router", "result": payload})


@research_app.command("eval-router")
def research_eval_router(
    dataset: str = typer.Option(
        ".binliquid/research/router_dataset.jsonl",
        help="Dataset JSONL path",
    ),
    model: str = typer.Option(
        "research/sltc_experiments/artifacts/router_model.json",
        help="Trained router model path",
    ),
    output_dir: str = typer.Option(
        "research/sltc_experiments/artifacts",
        help="Output directory",
    ),
) -> None:
    ensure_artifact_scaffold()
    payload = evaluate_router_model(dataset_path=dataset, model_path=model, output_dir=output_dir)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    write_artifact("research_summary", {"kind": "eval_router", "result": payload})


@research_app.command("calibrate-router")
def research_calibrate_router(
    dataset: str = typer.Option(
        ".binliquid/research/router_dataset.jsonl",
        help="Dataset JSONL path",
    ),
    output_dir: str = typer.Option(
        "research/sltc_experiments/artifacts",
        help="Output directory",
    ),
    seed: int = typer.Option(42, help="Random seed"),
) -> None:
    ensure_artifact_scaffold()
    payload = calibrate_router_params(dataset_path=dataset, output_dir=output_dir, seed=seed)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
    write_artifact("research_summary", {"kind": "calibrate_router", "result": payload})


if __name__ == "__main__":
    app()
