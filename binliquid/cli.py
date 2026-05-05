from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from benchmarks.run_ablation import run_ablation_benchmark, run_energy_benchmark
from benchmarks.run_smoke import run_smoke_benchmark
from benchmarks.run_team import run_team_benchmark
from binliquid import __version__
from binliquid.computer_use import ComputerUseMode
from binliquid.computer_use.runtime import ComputerUseRunner, SessionCommand
from binliquid.computer_use.vision_runtime.drivers.macos import MacOSVisionReadiness
from binliquid.computer_use.vision_runtime.platforms import build_platform_capabilities
from binliquid.computer_use.vision_runtime.provider_doctor import doctor_vision_provider
from binliquid.computer_use.vision_runtime.qualification import (
    missing_platform_qualification_result,
    run_macos_live_qualification,
    run_vision_qualification,
    validate_platform_qualification_report,
)
from binliquid.computer_use.vision_runtime.replay import (
    load_replay_summary,
    verify_qualification_report_replay,
    verify_replay,
)
from binliquid.contracts.version import OPERATOR_PANEL_CONTRACT_VERSION
from binliquid.core.llm_ollama import OllamaLLM, check_provider_chain
from binliquid.core.orchestrator import Orchestrator
from binliquid.core.planner import Planner
from binliquid.enterprise.baseline import enterprise_startup_abort, security_posture
from binliquid.enterprise.identity import (
    IdentityResolutionError,
    check_permission,
    describe_actor,
    require_permission,
)
from binliquid.enterprise.maintenance import (
    create_backup,
    export_support_bundle,
    ga_readiness_report,
    migration_apply,
    migration_plan,
    render_ga_readiness_markdown,
    restore_verify,
)
from binliquid.enterprise.observability import collect_metrics_snapshot
from binliquid.enterprise.qualification import run_qualification, write_qualification_report
from binliquid.enterprise.signing import (
    key_status,
    rotate_plan,
    verify_signed_artifact,
    write_signed_json,
)
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
from binliquid.runtime.platform import PlatformInfo, current_platform
from binliquid.schemas.models import ExpertName
from binliquid.team.continuation import (
    ResumeContinuationError,
    derive_resume_continuation_state,
)
from binliquid.team.models import TeamSpec
from binliquid.team.pilot_gate import run_pilot_check, write_pilot_report
from binliquid.team.replay import load_events, load_job_status, replay_job
from binliquid.team.supervisor import TeamSupervisor
from binliquid.team.validation import validate_team_spec
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
computer_use_app = typer.Typer(help="Computer use execution commands")
computer_use_vision_app = typer.Typer(help="Vision-first computer use commands")
computer_use_qualification_app = typer.Typer(help="Computer-use qualification commands")
computer_use_provider_app = typer.Typer(help="Computer-use provider readiness commands")
team_app = typer.Typer(help="Team runtime commands")
auth_app = typer.Typer(help="Enterprise identity commands")
security_app = typer.Typer(help="Enterprise security commands")
keys_app = typer.Typer(help="Enterprise key management commands")
migrate_app = typer.Typer(help="Migration commands")
backup_app = typer.Typer(help="Backup commands")
restore_app = typer.Typer(help="Restore commands")
support_app = typer.Typer(help="Support commands")
support_bundle_app = typer.Typer(help="Support bundle commands")
metrics_app = typer.Typer(help="Observability commands")
ga_app = typer.Typer(help="GA readiness commands")
qualification_app = typer.Typer(help="Qualification evidence commands")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(memory_app, name="memory")
app.add_typer(research_app, name="research")
app.add_typer(config_app, name="config")
app.add_typer(approval_app, name="approval")
app.add_typer(operator_app, name="operator")
app.add_typer(computer_use_app, name="computer-use")
computer_use_app.add_typer(computer_use_vision_app, name="vision")
computer_use_app.add_typer(computer_use_qualification_app, name="qualification")
computer_use_app.add_typer(computer_use_provider_app, name="provider")
app.add_typer(team_app, name="team")
app.add_typer(auth_app, name="auth")
app.add_typer(security_app, name="security")
app.add_typer(keys_app, name="keys")
app.add_typer(migrate_app, name="migrate")
app.add_typer(backup_app, name="backup")
app.add_typer(restore_app, name="restore")
app.add_typer(support_app, name="support")
support_app.add_typer(support_bundle_app, name="bundle")
app.add_typer(metrics_app, name="metrics")
app.add_typer(ga_app, name="ga")
app.add_typer(qualification_app, name="qualification")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def app_callback(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show BinLiquid core version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    _ = version


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


def _normalize_provider_name(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip().lower()
    if normalized in {"hf", "huggingface"}:
        return "transformers"
    return normalized


def _build_cli_overrides(
    *,
    provider: str | None = None,
    fallback_provider: str | None = None,
    model: str | None = None,
    hf_model_id: str | None = None,
) -> dict[str, str | None]:
    return {
        "llm_provider": provider,
        "fallback_provider": fallback_provider,
        "model_name": model,
        "hf_model_id": hf_model_id,
    }


def _validate_model_override_combo(
    *,
    effective_provider: str,
    model_override: str | None,
    hf_model_id_override: str | None,
) -> tuple[str, str] | None:
    normalized = _normalize_provider_name(effective_provider)
    if normalized == "transformers" and model_override is not None:
        return (
            "INVALID_MODEL_OVERRIDE",
            "model override (--model) cannot be used with provider=transformers.",
        )
    if normalized == "ollama" and hf_model_id_override is not None:
        return (
            "INVALID_HF_MODEL_ID_OVERRIDE",
            "hf model override (--hf-model-id) cannot be used with provider=ollama.",
        )
    return None


def _model_selection_context(
    *,
    config: RuntimeConfig,
    source_map: dict[str, str] | None,
) -> dict[str, str]:
    source_map = source_map or {}
    return {
        "requested_provider": str(config.llm_provider),
        "requested_fallback_provider": str(config.fallback_provider),
        "requested_model_name": str(config.model_name),
        "requested_hf_model_id": str(config.hf_model_id),
        "config_source_model_name": str(source_map.get("model_name", "profile")),
        "config_source_hf_model_id": str(source_map.get("hf_model_id", "profile")),
    }


def _startup_abort(config: RuntimeConfig, runtime: GovernanceRuntime | None) -> str | None:
    enterprise_error = enterprise_startup_abort(config)
    if enterprise_error:
        return f"ENTERPRISE_PREFLIGHT_FAILED: {enterprise_error}"
    return governance_startup_abort(config, runtime)


def _require_permission_or_exit(config: RuntimeConfig, permission: str):
    try:
        return require_permission(config, permission=permission)
    except IdentityResolutionError as exc:
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "error_code": exc.error_code,
                    "error": str(exc),
                    "permission": permission,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1) from None


def _supported_profiles() -> list[str]:
    config_dir = Path(__file__).resolve().parents[1] / "config"
    known_order = ["balanced", "restricted", "enterprise", "research", "lite", "default"]
    discovered = {
        path.stem
        for path in config_dir.glob("*.toml")
        if path.is_file() and path.stem != "policies"
    }
    ordered = [name for name in known_order if name in discovered]
    extras = sorted(discovered - set(ordered))
    return [*ordered, *extras]


def _with_contract_version(payload: dict[str, Any]) -> dict[str, Any]:
    return {"contract_version": OPERATOR_PANEL_CONTRACT_VERSION, **payload}


def _current_git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _load_json_file_if_present(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_computer_use_mode(mode: str) -> ComputerUseMode:
    normalized = mode.strip().lower()
    aliases = {
        "assisted": ComputerUseMode.STEP_APPROVAL,
        "step_approval": ComputerUseMode.STEP_APPROVAL,
        "step-approval": ComputerUseMode.STEP_APPROVAL,
        "supervised": ComputerUseMode.EXECUTE,
        "execute": ComputerUseMode.EXECUTE,
        "dry_run": ComputerUseMode.DRY_RUN,
        "dry-run": ComputerUseMode.DRY_RUN,
    }
    if normalized not in aliases:
        raise ValueError(f"unsupported computer use mode: {mode}")
    return aliases[normalized]


def _parse_computer_use_runtime(runtime: str) -> str:
    normalized = runtime.strip().lower().replace("_", "-")
    aliases = {
        "legacy-pilot": "legacy_pilot",
        "legacy": "legacy_pilot",
        "vision-first": "vision_first",
        "vision": "vision_first",
        "auto": "auto",
    }
    if normalized not in aliases:
        raise ValueError(f"unsupported computer use runtime: {runtime}")
    return aliases[normalized]


@config_app.command("resolve")
def config_resolve(
    profile: str = typer.Option("balanced", help="Config profile"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    cli_overrides = _build_cli_overrides(
        provider=provider,
        fallback_provider=fallback_provider,
        model=model,
        hf_model_id=hf_model_id,
    )
    resolved, source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=cli_overrides,
    )
    validation_error = _validate_model_override_combo(
        effective_provider=resolved.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        error_code, message = validation_error
        payload = {
            "profile": profile,
            "status": "invalid_input",
            "error_code": error_code,
            "error": message,
        }
        if json_output:
            typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            typer.echo(f"error_code={error_code}")
            typer.echo(message)
        raise typer.Exit(code=1)

    payload = _with_contract_version(
        {
        "profile": profile,
        "status": "ok",
        "resolved": redact_config_payload(resolved.model_dump(mode="python")),
        "source_map": source_map,
        }
    )
    if json_output:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        typer.echo(f"profile={profile}")
        typer.echo(f"router_mode={resolved.router_mode}")
        typer.echo(f"shadow_router_enabled={resolved.shadow_router_enabled}")
        typer.echo(f"shadow_router_mode={resolved.shadow_router_mode}")


@app.command()
def doctor(
    profile: str = typer.Option("lite", help="Config profile name"),
    provider: str | None = typer.Option(
        None,
        help="Override provider: auto|ollama|transformers",
    ),
    fallback_provider: str | None = typer.Option(
        None,
        help="Override fallback provider: transformers|ollama",
    ),
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    """Runtime and provider health check."""
    ensure_artifact_scaffold()
    config, source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=config.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        error_code, message = validation_error
        payload = {
            "profile": profile,
            "requested_provider": config.llm_provider,
            "requested_fallback_provider": config.fallback_provider,
            "requested_model_name": config.model_name,
            "requested_hf_model_id": config.hf_model_id,
            "selected_provider": None,
            "effective_model_name": None,
            "effective_hf_model_id": None,
            "fallback_used": False,
            "status": "invalid_input",
            "error_code": error_code,
            "error": message,
            "config_source_model_name": source_map.get("model_name", "profile"),
            "config_source_hf_model_id": source_map.get("hf_model_id", "profile"),
        }
        if json_output:
            typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            typer.echo(f"status={payload['status']} error={payload['error_code']}")
        write_artifact("status", payload)
        raise typer.Exit(code=1)

    try:
        status = check_provider_chain(
            model_name=config.model_name,
            provider_name=config.llm_provider,
            fallback_provider=config.fallback_provider,
            fallback_enabled=config.fallback_enabled,
            hf_model_id=config.hf_model_id,
            device=config.device,
        )
    except ValueError as exc:
        payload = {
            "profile": profile,
            "requested_provider": config.llm_provider,
            "requested_fallback_provider": config.fallback_provider,
            "requested_model_name": config.model_name,
            "requested_hf_model_id": config.hf_model_id,
            "selected_provider": None,
            "effective_model_name": None,
            "effective_hf_model_id": None,
            "fallback_used": False,
            "status": "invalid_input",
            "error_code": "INVALID_PROVIDER",
            "error": str(exc),
            "config_source_model_name": source_map.get("model_name", "profile"),
            "config_source_hf_model_id": source_map.get("hf_model_id", "profile"),
        }
        if json_output:
            typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            typer.echo(f"status={payload['status']} error={payload['error_code']}")
        write_artifact("status", payload)
        raise typer.Exit(code=1) from None

    status.setdefault("requested_provider", config.llm_provider)
    status.setdefault("requested_fallback_provider", config.fallback_provider)
    status.setdefault("requested_model_name", config.model_name)
    status.setdefault("requested_hf_model_id", config.hf_model_id)
    status.setdefault("effective_model_name", None)
    status.setdefault("effective_hf_model_id", None)
    status.setdefault("fallback_used", False)
    status["config_source_model_name"] = source_map.get("model_name", "profile")
    status["config_source_hf_model_id"] = source_map.get("hf_model_id", "profile")
    status["profile"] = profile

    status_value = str(status.get("status", "")).lower()
    if status_value not in {"healthy", "degraded_fallback", "unrunnable", "invalid_input"}:
        selected = str(status.get("selected_provider", ""))
        primary = status.get("primary", {})
        if selected == "ollama":
            daemon_ok = bool(primary.get("daemon_ok", False))
            model_present = bool(primary.get("model_present", False))
            status_value = "healthy" if (daemon_ok and model_present) else "unrunnable"
        else:
            status_value = "healthy"
        status["status"] = status_value

    if json_output:
        typer.echo(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        typer.echo(f"status={status.get('status')} provider={status.get('selected_provider')}")
    write_artifact(
        "status",
        status,
    )

    if status_value == "invalid_input":
        raise typer.Exit(code=1)
    if status_value == "unrunnable":
        raise typer.Exit(code=3)


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
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
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
    config, source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=config.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        _code, message = validation_error
        typer.echo(message)
        raise typer.Exit(code=1)

    if debug:
        config = config.model_copy(update={"debug_mode": True})
    if privacy_off:
        config = config.model_copy(update={"privacy_mode": False})
    _require_permission_or_exit(config, "runtime.run")

    orchestrator = _build_orchestrator(
        config,
        router_mode=router_mode,
        provider_name=config.llm_provider,
        fallback_provider=config.fallback_provider,
    )
    startup_error = _startup_abort(
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
        context.update(_model_selection_context(config=config, source_map=source_map))
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


def _redact_snapshot_payload(value: object) -> object:
    sensitive_markers = ("token", "secret", "password", "key", "user_input", "payload")
    if isinstance(value, dict):
        redacted: dict[str, object] = {}
        for key, inner in value.items():
            lowered = key.lower()
            if any(marker in lowered for marker in sensitive_markers):
                redacted[key] = "***REDACTED***"
                continue
            redacted[key] = _redact_snapshot_payload(inner)
        return redacted
    if isinstance(value, list):
        return [_redact_snapshot_payload(item) for item in value]
    return value


def _parse_iso_datetime(value: str) -> datetime:
    normalized = value.strip()
    if not normalized:
        raise ValueError("empty datetime")
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _collect_resume_overrides(
    *,
    events: list[dict[str, object]],
    governance_runtime: GovernanceRuntime | None,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    if governance_runtime is None:
        return {}, []
    governance_runtime.approval_store.expire_pending()

    overrides: dict[str, dict[str, str]] = {}
    resolved: list[dict[str, str]] = []
    for item in events:
        if str(item.get("event") or "") != "approval_requested":
            continue
        task_id = str(item.get("task_id") or "").strip()
        data = item.get("data")
        if not isinstance(data, dict):
            continue
        approval_id = str(data.get("approval_id") or "").strip()
        if not task_id or not approval_id:
            continue

        target = _normalize_resume_target(str(data.get("target") or "handoff"))
        ticket = governance_runtime.approval_store.get(approval_id)
        if ticket is None:
            continue
        status = ticket.status.value
        if status != "executed":
            continue
        if ticket.execution_status.value != "executed":
            continue
        if ticket.consumed_at is not None or ticket.consumed_by_job_id is not None:
            continue
        overrides.setdefault(task_id, {})[target] = approval_id
        resolved.append(
            {
                "task_id": task_id,
                "target": target,
                "approval_id": approval_id,
                "status": status,
            }
        )
    return overrides, resolved


def _normalize_resume_target(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"task", "handoff", "memory_write"}:
        return normalized
    return "handoff"


def _team_init_template(template_name: str) -> str:
    normalized = template_name.strip().lower()
    if normalized == "balanced":
        return """version: "1"
team:
  team_id: "aegis-team"
  supervisor_policy: "sequential_then_parallel"
  agents:
    - agent_id: "agent-intake"
      role: "Intake Agent"
      allowed_task_types: ["chat", "plan"]
      profile_name: "balanced"
      model_overrides: {}
      memory_scope_access: ["session", "case"]
      tool_policy_profile: "default"
      approval_mode: "auto"
    - agent_id: "agent-research"
      role: "Research Analyst Agent"
      allowed_task_types: ["research", "plan"]
      profile_name: "balanced"
      model_overrides: {}
      memory_scope_access: ["team", "case"]
      tool_policy_profile: "default"
      approval_mode: "auto"
    - agent_id: "agent-review"
      role: "Reviewer/QA Agent"
      allowed_task_types: ["chat", "plan"]
      profile_name: "balanced"
      model_overrides: {}
      memory_scope_access: ["case"]
      tool_policy_profile: "default"
      approval_mode: "always"
  handoff_rules: []
  termination_rules:
    max_tasks: 64
    max_retries: 1
    max_handoff_depth: 8
tasks: []
"""
    if normalized in {"regulated", "restricted"}:
        return """version: "1"
team:
  team_id: "aegis-regulated-team"
  supervisor_policy: "sequential_then_parallel"
  agents:
    - agent_id: "agent-intake"
      role: "Intake Agent"
      allowed_task_types: ["chat", "plan"]
      profile_name: "restricted"
      model_overrides: {}
      memory_scope_access: ["session", "case"]
      tool_policy_profile: "restricted"
      approval_mode: "auto"
    - agent_id: "agent-research"
      role: "Research Analyst Agent"
      allowed_task_types: ["research", "plan"]
      profile_name: "restricted"
      model_overrides: {}
      memory_scope_access: ["case"]
      tool_policy_profile: "restricted"
      approval_mode: "auto"
    - agent_id: "agent-compliance"
      role: "Policy/Compliance Agent"
      allowed_task_types: ["plan"]
      profile_name: "restricted"
      model_overrides: {}
      memory_scope_access: ["case"]
      tool_policy_profile: "restricted"
      approval_mode: "always"
    - agent_id: "agent-execution"
      role: "Execution Agent"
      allowed_task_types: ["mixed", "code"]
      profile_name: "restricted"
      model_overrides: {}
      memory_scope_access: ["session"]
      tool_policy_profile: "restricted"
      approval_mode: "always"
    - agent_id: "agent-review"
      role: "Reviewer/QA Agent"
      allowed_task_types: ["chat", "plan"]
      profile_name: "restricted"
      model_overrides: {}
      memory_scope_access: ["case"]
      tool_policy_profile: "restricted"
      approval_mode: "always"
  handoff_rules: []
  termination_rules:
    max_tasks: 64
    max_retries: 1
    max_handoff_depth: 8
tasks: []
"""
    raise ValueError("unsupported template. use one of: balanced, regulated")


def _load_team_spec(spec_path: str | Path) -> TeamSpec:
    path = Path(spec_path)
    if not path.exists():
        raise FileNotFoundError(f"team spec not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
    elif suffix == ".toml":
        with path.open("rb") as file_obj:
            payload = tomllib.load(file_obj)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "YAML support requires PyYAML. Use .json/.toml or install pyyaml."
            ) from exc
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        raise ValueError("Unsupported team spec format. Use .json, .toml, .yaml, or .yml.")

    return TeamSpec.model_validate(payload)


@approval_app.command("pending")
def approval_pending(
    profile: str = typer.Option("balanced", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    _require_permission_or_exit(config, "approval.decide")
    runtime = _build_governance_runtime(config)
    if runtime is None:
        typer.echo("Governance disabled.")
        raise typer.Exit(code=1)
    tickets = [item.model_dump(mode="json") for item in runtime.approval_store.list_pending()]
    if json_output:
        typer.echo(
            json.dumps(
                _with_contract_version({"pending": tickets}),
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        typer.echo(f"pending_count={len(tickets)}")
        for item in tickets:
            typer.echo(
                f"- {item['approval_id']} status={item['status']} "
                f"expires_at={item['expires_at']} run_id={item['run_id']}"
            )


@approval_app.command("show")
def approval_show(
    approval_id: str = typer.Option(..., "--id", help="Approval ticket id"),
    profile: str = typer.Option("balanced", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
    show_raw_snapshot: bool = typer.Option(
        False,
        "--show-raw-snapshot",
        help="Include raw snapshot payload.",
    ),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runtime = _build_governance_runtime(config)
    if runtime is None:
        typer.echo("Governance disabled.")
        raise typer.Exit(code=1)

    runtime.approval_store.expire_pending()
    ticket = runtime.approval_store.get(approval_id)
    if ticket is None:
        payload = {"approval_id": approval_id, "error_code": "APPROVAL_NOT_FOUND"}
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo("APPROVAL_NOT_FOUND")
        raise typer.Exit(code=1)

    ticket_payload = ticket.model_dump(mode="json")
    ticket_payload["snapshot"] = (
        ticket.snapshot if show_raw_snapshot else _redact_snapshot_payload(ticket.snapshot)
    )
    payload = _with_contract_version(
        {
            "approval_id": approval_id,
            "status": ticket.status.value,
            "execution_status": ticket.execution_status.value,
            "ticket": ticket_payload,
        }
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(
            f"approval_id={approval_id} status={ticket.status.value} "
            f"execution_status={ticket.execution_status.value}"
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
    _require_permission_or_exit(config, "approval.decide")
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
    payload = _with_contract_version(
        {
            "approval_id": approval_id,
            "error_code": result.error_code,
            "ticket": result.ticket.model_dump(mode="json") if result.ticket else None,
        }
    )
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
    _require_permission_or_exit(config, "approval.execute")
    runtime = _build_governance_runtime(config)
    if runtime is None:
        typer.echo("Governance disabled.")
        raise typer.Exit(code=1)

    startup_error = _startup_abort(config, runtime)
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
        "requested_provider": str(config.llm_provider),
        "requested_fallback_provider": str(config.fallback_provider),
        "requested_model_name": str(config.model_name),
        "requested_hf_model_id": str(config.hf_model_id),
        "config_source_model_name": "profile",
        "config_source_hf_model_id": "profile",
    }
    result = orchestrator.process(
        str(ticket.snapshot.get("user_input", "")),
        session_context=context,
        use_router=True,
    )
    output = _with_contract_version(
        {
            "approval_id": approval_id,
            "actor": actor,
            "execution_used_path": result.used_path,
            "trace_id": result.trace_id,
            "fallback_events": result.fallback_events,
            "metrics": result.metrics,
        }
    )
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
    _require_permission_or_exit(config, "audit.read")
    runtime = _build_governance_runtime(config)
    startup_error = _startup_abort(config, runtime)
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


def _computer_use_vision_runtime_payload(
    vision_config: Any,
    *,
    platform_label: str,
) -> dict[str, Any]:
    qualification_reports = {}
    macos_report = _load_json_file_if_present(vision_config.macos_qualification_report)
    if macos_report is not None:
        qualification_reports["macos"] = macos_report
    platform_capabilities = build_platform_capabilities(
        vision_config,
        qualification_reports=qualification_reports,
        commit=_current_git_sha(),
    )
    current_label = platform_label if platform_label in platform_capabilities else "macos"
    current_capability = platform_capabilities[current_label]
    provider_configured = vision_config.vision_provider == "mock" or bool(
        vision_config.vision_provider != "none" and vision_config.vision_model
    )
    return {
        "enabled": current_capability.live_enabled,
        "stage": current_capability.stage,
        "platform": platform_label if platform_label in platform_capabilities else "unknown",
        "scope": "vision_first_desktop_web_file",
        "executionModes": current_capability.execution_modes,
        "replayable": True,
        "failClosed": True,
        "reasonCode": current_capability.reason_code,
        "summary": current_capability.summary,
        "provider": {
            "kind": vision_config.vision_provider,
            "name": vision_config.vision_provider,
            "configured": provider_configured,
            "model": vision_config.vision_model,
            "strictJson": True,
        },
        "safety": {
            "rawScreenshotPersistence": vision_config.raw_screenshot_persistence,
            "rawScreenshotRetention": vision_config.raw_screenshot_retention,
            "rawScreenshotMaxCount": vision_config.raw_screenshot_max_count,
            "terminalControl": vision_config.terminal_control,
            "sensitiveSurfacePolicy": vision_config.sensitive_surface_policy,
            "approvalRequiredForRiskyActions": True,
            "sensitiveSurfaceBlocked": True,
            "approvalFreshnessEnforced": True,
            "replayIntegrityVerified": True,
        },
        "platforms": {
            key: capability.model_dump(mode="json", by_alias=True)
            for key, capability in platform_capabilities.items()
        },
    }


@operator_app.command("capabilities")
def operator_capabilities(
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    platform_info = current_platform()
    windows_computer_use = platform_info.label == "windows"
    vision_config = RuntimeConfig.from_profile("balanced").computer_use
    computer_use_pilot = (
        {
            "enabled": False,
            "stage": "not_qualified",
            "platform": "windows",
            "scope": "core+operator_panel+bundled_runtime",
            "executionModes": [],
            "replayable": True,
            "failClosed": True,
            "adapterStatus": "windows_scaffold",
            "reasonCode": "WINDOWS_COMPUTER_USE_NOT_QUALIFIED",
            "summary": (
                "Windows core/operator support is available; Windows live computer-use "
                "automation is not qualified."
            ),
        }
        if windows_computer_use
        else {
            "enabled": True,
            "stage": "execution_slice",
            "platform": "macos",
            "scope": "browser+desktop+file",
            "executionModes": ["dry_run", "step_approval", "execute"],
            "replayable": True,
            "failClosed": True,
            "adapterStatus": "safari_applescript",
            "reasonCode": "MACOS_COMPUTER_USE_PILOT",
            "summary": (
                "macOS computer-use pilot is qualification-gated behind "
                "fail-closed controls."
            ),
        }
    )
    computer_use_vision_runtime = _computer_use_vision_runtime_payload(
        vision_config,
        platform_label=platform_info.label,
    )
    payload = {
        "coreVersion": __version__,
        "contractVersion": OPERATOR_PANEL_CONTRACT_VERSION,
        "profiles": _supported_profiles(),
        "features": {
            "operatorWorkflowParity": True,
            "enterpriseOpsParity": True,
            "computerUsePilot": computer_use_pilot,
            "computerUseVisionRuntime": computer_use_vision_runtime,
        },
        "commands": {
            "teamSubmit": True,
            "teamResumeSubmit": True,
            "teamListJson": True,
            "teamStatusJson": True,
            "teamReplayJson": True,
            "approvalShowJson": True,
            "approvalPendingJson": True,
            "approvalDecide": True,
            "approvalExecute": True,
            "configResolveJson": True,
            "authWhoamiJson": True,
            "authCheckJson": True,
            "securityBaselineJson": True,
            "keysStatusJson": True,
            "keysVerifyJson": True,
            "keysRotatePlanJson": True,
            "backupCreateJson": True,
            "backupVerifyJson": True,
            "restoreVerifyJson": True,
            "supportBundleExportJson": True,
            "metricsSnapshotJson": True,
            "gaReadinessJson": True,
            "qualificationRunJson": True,
            "migratePlanJson": True,
            "migrateApplyDryRunJson": True,
            "computerUseSubmit": True,
            "computerUsePause": True,
            "computerUseResume": True,
            "computerUseStop": True,
            "computerUseStateJson": True,
        },
        "artifactSchema": {
            "auditEnvelope": "3",
            "events": "3",
            "gaReadinessReport": "1",
            "securityPosture": "1",
        },
    }
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(
            f"coreVersion={payload['coreVersion']} contractVersion={payload['contractVersion']}"
        )


@computer_use_vision_app.command("doctor")
def computer_use_vision_doctor(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str = typer.Option(
        "macos",
        "--platform",
        help="Platform to inspect: macos|windows|linux",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    normalized_platform = platform.strip().lower()
    if normalized_platform not in {"macos", "windows", "linux"}:
        raise typer.BadParameter("platform must be macos, windows, or linux")
    platform_info = current_platform()
    if normalized_platform != platform_info.label:
        platform_info = PlatformInfo(
            system=platform_info.system,
            label=normalized_platform,
            machine=platform_info.machine,
            release=platform_info.release,
        )
    qualification_report = _load_json_file_if_present(
        config.computer_use.macos_qualification_report
    )
    report = MacOSVisionReadiness(config.computer_use).evaluate(
        platform_info=platform_info,
        environment=dict(os.environ),
        qualification_report=qualification_report,
        commit=_current_git_sha(),
    )
    payload = _with_contract_version(report)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["stage"])


@computer_use_app.command("doctor")
def computer_use_doctor(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str = typer.Option(
        "all",
        "--platform",
        help="Platform to inspect: all|macos|windows|linux",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    qualification_reports = {}
    macos_report = _load_json_file_if_present(config.computer_use.macos_qualification_report)
    if macos_report is not None:
        qualification_reports["macos"] = macos_report
    capabilities = build_platform_capabilities(
        config.computer_use,
        qualification_reports=qualification_reports,
        commit=_current_git_sha(),
    )
    selected = platform.strip().lower()
    if selected != "all":
        if selected not in capabilities:
            raise typer.BadParameter("platform must be all, macos, windows, or linux")
        capabilities = {selected: capabilities[selected]}
    base_payload: dict[str, Any] = {
        "runtime": "computer_use_vision",
        "profile": profile,
        "currentPlatform": current_platform().label,
        "platforms": {
            key: capability.model_dump(mode="json", by_alias=True)
            for key, capability in capabilities.items()
        },
    }
    if selected == "macos":
        base_payload.update(
            MacOSVisionReadiness(config.computer_use).evaluate(
                platform_info=PlatformInfo(
                    system=current_platform().system,
                    label="macos",
                    machine=current_platform().machine,
                    release=current_platform().release,
                ),
                environment=dict(os.environ),
                qualification_report=macos_report,
                commit=_current_git_sha(),
            )
        )
    payload = _with_contract_version(base_payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"platforms={','.join(payload['platforms'])}")


@computer_use_provider_app.command("doctor")
def computer_use_provider_doctor(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    provider: str = typer.Option("ollama", "--provider", help="Local provider to inspect"),
    model: str | None = typer.Option(None, "--model", help="Configured local vision model"),
    synthetic_fixture: bool = typer.Option(
        False,
        "--synthetic-fixture/--no-synthetic-fixture",
        help="Use a synthetic non-sensitive fixture image; required for readiness.",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    selected_model = model or config.computer_use.vision_model
    payload = doctor_vision_provider(
        provider=provider,
        model=selected_model,
        synthetic_fixture=synthetic_fixture,
        timeout_s=config.computer_use.vision_provider_timeout_s,
        max_retries=config.computer_use.vision_provider_max_retries,
        environment=os.environ,
    )
    payload = _with_contract_version(payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(payload.get("status")))


@computer_use_qualification_app.command("run")
def computer_use_qualification_run(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str = typer.Option("macos", "--platform", help="macos"),
    suite: str = typer.Option("live-fixture-smoke", "--suite", help="Qualification suite"),
    mode: str = typer.Option("supervised", "--mode", help="preflight|supervised"),
    provider: str | None = typer.Option(None, "--provider", help="Override vision provider"),
    model: str | None = typer.Option(None, "--model", help="Override vision model"),
    output: str = typer.Option(
        "artifacts/computer_use/macos_qualification_report.json",
        "--output",
        help="Qualification report output path",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    normalized_platform = platform.strip().lower()
    if normalized_platform != "macos":
        payload = _with_contract_version(
            {
                "schemaVersion": "1.0",
                "platform": normalized_platform,
                "status": "blocked",
                "stage": "not_qualified",
                "reasonCode": f"{normalized_platform.upper()}_COMPUTER_USE_NOT_QUALIFIED",
                "blockers": [f"{normalized_platform.upper()}_COMPUTER_USE_NOT_QUALIFIED"],
            }
        )
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if mode.strip().lower() not in {"preflight", "supervised"}:
        raise typer.BadParameter("mode must be preflight or supervised for macOS qualification")
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    computer_use_config = config.computer_use
    if provider is not None or model is not None:
        updates: dict[str, Any] = {}
        if provider is not None:
            updates["vision_provider"] = provider
        if model is not None:
            updates["vision_model"] = model
        computer_use_config = computer_use_config.model_copy(update=updates)
    report_payload = run_macos_live_qualification(
        config=computer_use_config,
        suite=suite,
        mode=mode,
        output_path=Path(output),
        env=os.environ,
    )
    payload = _with_contract_version(report_payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(payload.get("status")))


@computer_use_qualification_app.command("verify")
def computer_use_qualification_verify(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str | None = typer.Option(None, "--platform", help="macos|windows|linux"),
    report: str | None = typer.Option(None, "--report", help="Qualification report JSON path"),
    schema: str | None = typer.Option(
        None,
        "--schema",
        help="Qualification JSON schema path for fixture validation",
    ),
    input_path: str | None = typer.Option(
        None,
        "--input",
        help="Qualification fixture JSON path for static validation",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    if input_path is not None:
        payload = _verify_computer_use_qualification_fixture(
            schema_path=Path(schema) if schema else None,
            input_path=Path(input_path),
        )
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(payload["status"])
        if payload["status"] != "pass":
            raise typer.Exit(code=1)
        return

    if platform is None or report is None:
        raise typer.BadParameter("provide either --schema/--input or --platform/--report")

    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    normalized_platform = platform.strip().lower()
    report_path = Path(report)
    if report_path.exists():
        validation = validate_platform_qualification_report(
            json.loads(report_path.read_text(encoding="utf-8")),
            platform=normalized_platform,
            config=config.computer_use,
            commit=_current_git_sha(),
        )
    else:
        validation = missing_platform_qualification_result(normalized_platform)
    payload = validation.model_dump(mode="json")
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(validation.status)
    if not validation.allowed:
        raise typer.Exit(code=1)


def _verify_computer_use_qualification_fixture(
    *,
    schema_path: Path | None,
    input_path: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not input_path.exists():
        return {
            "status": "fail",
            "allowed": False,
            "blockers": ["VISION_PLATFORM_QUALIFICATION_MISSING"],
            "inputPath": str(input_path),
        }
    fixture = json.loads(input_path.read_text(encoding="utf-8"))
    if schema_path is not None:
        if not schema_path.exists():
            blockers.append("VISION_PLATFORM_QUALIFICATION_SCHEMA_MISSING")
        else:
            blockers.extend(_validate_json_schema(schema_path, fixture))

    fixture_platform = str(fixture.get("platform", "")).strip().lower()
    fixture_config = _fixture_runtime_config(fixture)
    validation = validate_platform_qualification_report(
        fixture,
        platform=fixture_platform,
        config=fixture_config,
        commit=str(fixture.get("commit", "")),
    )
    blockers.extend(validation.blockers)
    checks = _qualification_fixture_checks(fixture)
    blockers.extend(reason for reason, ok in checks.items() if not ok)

    return {
        "status": "pass" if not blockers else "fail",
        "allowed": False,
        "reviewOnly": True,
        "runtimeLiveEnabled": False,
        "schemaPath": str(schema_path) if schema_path else None,
        "inputPath": str(input_path),
        "platform": fixture_platform or None,
        "fixtureStatus": validation.status,
        "checks": checks,
        "blockers": blockers,
    }


def _validate_json_schema(schema_path: Path, fixture: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ModuleNotFoundError:
        return []
    schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema_payload).validate(fixture)
    except jsonschema.ValidationError as exc:
        return [f"VISION_PLATFORM_QUALIFICATION_SCHEMA_INVALID:{exc.json_path}"]
    return []


def _fixture_runtime_config(fixture: dict[str, Any]) -> Any:
    platform = str(fixture.get("platform", "")).strip().lower()
    provider = fixture.get("provider") if isinstance(fixture.get("provider"), dict) else {}
    backends = fixture.get("backends") if isinstance(fixture.get("backends"), dict) else {}
    updates: dict[str, Any] = {
        "vision_enabled": True,
        "vision_provider": str(provider.get("name") or "none"),
        "vision_model": str(provider.get("model") or "") or None,
    }
    if platform in {"macos", "windows", "linux"}:
        updates[f"{platform}_live_enabled"] = True
        updates[f"{platform}_capture_backend"] = str(backends.get("capture", "disabled"))
        updates[f"{platform}_input_backend"] = str(backends.get("input", "disabled"))
    return RuntimeConfig().computer_use.model_copy(update=updates)


def _qualification_fixture_checks(fixture: dict[str, Any]) -> dict[str, bool]:
    safety = fixture.get("safety") if isinstance(fixture.get("safety"), dict) else {}
    raw_count = safety.get(
        "rawScreenshotsPersisted",
        fixture.get("artifacts", {}).get("rawScreenshotCount", -1)
        if isinstance(fixture.get("artifacts"), dict)
        else -1,
    )
    return {
        "has_platform_identity": bool(fixture.get("platform")),
        "has_config_hash": bool(fixture.get("configHash")),
        "has_safety_invariants": bool(safety),
        "approval_freshness_enforced": safety.get("approvalFreshnessEnforced") is True,
        "replay_integrity_verified": (
            safety.get("replayIntegrityVerified") is True
            or safety.get("replayIntegrityEnforced") is True
        ),
        "raw_screenshots_not_persisted": int(raw_count) == 0,
        "has_evidence_placeholders": isinstance(fixture.get("evidence", []), list),
        "does_not_enable_live_runtime": True,
    }


@computer_use_app.command("replay")
def computer_use_replay(
    job_id: str | None = typer.Option(None, "--job-id", help="Vision computer-use job id"),
    report: str | None = typer.Option(
        None,
        "--report",
        help="macOS qualification report JSON path",
    ),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    verify: bool = typer.Option(False, "--verify/--no-verify", help="Verify replay integrity"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    if report is not None:
        payload = _with_contract_version(verify_qualification_report_replay(Path(report)))
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(f"report={report} verified={payload.get('verified')}")
        if verify and not payload.get("verified"):
            raise typer.Exit(code=1)
        return
    if job_id is None:
        raise typer.BadParameter("provide --job-id or --report")
    config = RuntimeConfig.from_profile(profile)
    job_dir = Path(root_dir or config.team.artifact_dir) / job_id
    payload = load_replay_summary(job_dir)
    if verify:
        payload["verification"] = verify_replay(job_dir)
    payload = _with_contract_version(payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} verified={payload.get('verified')}")


@computer_use_app.command("qualify")
def computer_use_qualify(
    runtime: str = typer.Option("vision-first", "--runtime", help="vision-first"),
    suite: str = typer.Option("smoke", "--suite", help="Qualification suite"),
    mode: str = typer.Option("deterministic", "--mode", help="deterministic|live"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    task_path: str = typer.Option(
        "benchmarks/tasks/computer_use_vision/smoke_tasks.jsonl",
        "--task-path",
        help="Qualification task JSONL path",
    ),
    output_root: str = typer.Option(
        "artifacts/computer_use_vision_qualification",
        "--output-root",
        help="Qualification output root",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    if _parse_computer_use_runtime(runtime) != "vision_first":
        payload = _with_contract_version(
            {
                "artifact_version": "computer_use_vision_qualification/v1",
                "status": "blocked",
                "blocking_reasons": ["UNSUPPORTED_RUNTIME"],
            }
        )
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        raise typer.Exit(code=1)
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    payload = run_vision_qualification(
        config=config.computer_use,
        mode=mode,
        suite=suite,
        task_path=Path(task_path),
        output_root=Path(output_root),
    )
    payload = _with_contract_version(payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["status"])


@computer_use_app.command("run")
def computer_use_run(
    once: str = typer.Option(..., "--once", help="Computer-use request"),
    job_id: str | None = typer.Option(None, "--job-id", help="Explicit job id"),
    case_id: str | None = typer.Option(None, "--case-id", help="Optional case id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    mode: str = typer.Option("supervised", "--mode", help="assisted|supervised|dry-run"),
    runtime: str = typer.Option(
        "legacy-pilot",
        "--runtime",
        help="legacy-pilot|vision-first|auto",
    ),
    max_steps: int | None = typer.Option(None, "--max-steps", help="Vision runtime step budget"),
    raw_screenshots: bool = typer.Option(
        False,
        "--raw-screenshots/--no-raw-screenshots",
        help="Persist raw screenshots only when explicitly enabled by config and request.",
    ),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model"),
    hf_model_id: str | None = typer.Option(None, "--hf-model-id", help="Override HF model id"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    resolved_mode = _parse_computer_use_mode(mode)
    config, _source_map = resolve_runtime_config(
        profile=profile,
        root_dir=Path.cwd(),
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    _require_permission_or_exit(config, "runtime.run")
    effective_root = root_dir or config.team.artifact_dir
    effective_job_id = job_id or f"cu-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    runner = ComputerUseRunner(config=config, root_dir=effective_root)
    try:
        payload = runner.run(
            prompt=once,
            job_id=effective_job_id,
            case_id=case_id,
            mode=resolved_mode,
            runtime_mode=_parse_computer_use_runtime(runtime),
            max_steps=max_steps,
            raw_screenshots=raw_screenshots,
        )
    except Exception as exc:  # noqa: BLE001
        payload = _with_contract_version(
            {
                "status": "error",
                "job_id": effective_job_id,
                "root_dir": effective_root,
                "error": str(exc),
            }
        )
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(str(exc))
        raise typer.Exit(code=1) from None

    output = _with_contract_version(
        {
            "status": "ok",
            "job_id": effective_job_id,
            "root_dir": effective_root,
            **payload,
        }
    )
    if json_output:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={effective_job_id} status={payload['job']['status']}")


@computer_use_app.command("pause")
def computer_use_pause(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = _with_contract_version(
        runner.request_control(job_id=job_id, command=SessionCommand.PAUSE)
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} requested=pause")


@computer_use_app.command("resume")
def computer_use_resume(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    try:
        payload = _with_contract_version(
            runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps(
                _with_contract_version({"status": "error", "job_id": job_id, "error": str(exc)}),
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1) from None
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} requested=resume")


@computer_use_app.command("stop")
def computer_use_stop(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = _with_contract_version(
        runner.request_control(job_id=job_id, command=SessionCommand.STOP)
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} requested=stop")


@computer_use_app.command("state")
def computer_use_state(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = _with_contract_version(runner.session_state(job_id=job_id))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(
            f"job_id={job_id} state={payload.get('computer_use', {}).get('lifecycle_state')}"
        )


@team_app.command("init")
def team_init(
    output: str = typer.Option("team.yaml", "--output", help="Target team spec path"),
    template_name: str = typer.Option(
        "balanced",
        "--template",
        help="Template preset: balanced|regulated",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file"),
) -> None:
    path = Path(output)
    if path.exists() and not force:
        typer.echo("Spec file already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    try:
        template = _team_init_template(template_name)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=2) from None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template, encoding="utf-8")
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "spec_path": str(path),
                "template": template_name,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


@team_app.command("validate")
def team_validate(
    spec: str = typer.Option(..., "--spec", help="Team spec path (.yaml/.json/.toml)"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    try:
        parsed = _load_team_spec(spec)
    except Exception as exc:  # noqa: BLE001
        payload = {"status": "invalid", "error": str(exc), "spec": spec}
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(f"invalid: {exc}")
        raise typer.Exit(code=1) from None

    payload = {
        "status": "ok",
        "team_id": parsed.team.team_id,
        "agent_count": len(parsed.team.agents),
        "task_count": len(parsed.tasks),
        "roles": [item.role for item in parsed.team.agents],
    }
    validation_errors = validate_team_spec(parsed)
    if validation_errors:
        payload = {
            "status": "invalid",
            "error": "runtime contract validation failed",
            "spec": spec,
            "errors": validation_errors,
        }
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo("invalid: runtime contract validation failed")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"team_id={payload['team_id']} agent_count={payload['agent_count']}")


@team_app.command("list")
def team_list(
    root_dir: str = typer.Option(
        ".binliquid/team/jobs",
        "--root-dir",
        help="Team artifact root directory",
    ),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Return jobs created at or after this ISO-8601 timestamp.",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    since_dt = None
    if since is not None:
        try:
            since_dt = _parse_iso_datetime(since)
        except ValueError:
            typer.echo(
                json.dumps(
                    {
                        "status": "error",
                        "error_code": "INVALID_INPUT",
                        "error": "Invalid --since value; expected ISO-8601 datetime.",
                        "since": since,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise typer.Exit(code=2) from None

    base = Path(root_dir)
    if not base.exists():
        payload = _with_contract_version(
            {"status": "ok", "root_dir": str(base), "count": 0, "items": [], "errors": []}
        )
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo("count=0")
        return

    items: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for job_dir in sorted(base.iterdir(), key=lambda p: p.name):
        if not job_dir.is_dir():
            continue
        status_path = job_dir / "status.json"
        if not status_path.exists():
            continue
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append({"job_id": job_dir.name, "error": str(exc)})
            continue
        job = payload.get("job")
        if not isinstance(job, dict):
            errors.append({"job_id": job_dir.name, "error": "invalid status payload"})
            continue

        created_at = str(job.get("created_at") or "")
        if since_dt is not None:
            try:
                created_at_dt = _parse_iso_datetime(created_at)
            except ValueError:
                errors.append({"job_id": job_dir.name, "error": "invalid created_at format"})
                continue
            if created_at_dt < since_dt:
                continue

        items.append(
            {
                "job_id": str(job.get("job_id") or job_dir.name),
                "case_id": str(job.get("case_id") or ""),
                "team_id": str(job.get("team_id") or ""),
                "status": str(job.get("status") or ""),
                "request": str(job.get("request") or ""),
                "created_at": created_at,
                "finished_at": str(job.get("finished_at") or ""),
                "audit_envelope_path": str(payload.get("audit_envelope_path") or ""),
                "job_dir": str(job_dir),
            }
        )

    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    output = _with_contract_version(
        {
            "status": "ok",
            "root_dir": str(base),
            "count": len(items),
            "items": items,
            "errors": errors,
        }
    )
    if json_output:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"count={len(items)}")
        for item in items:
            typer.echo(
                f"- {item['job_id']} status={item['status']} "
                f"team_id={item['team_id']} created_at={item['created_at']}"
            )


@team_app.command("run")
def team_run(
    spec: str = typer.Option(..., "--spec", help="Team spec path"),
    once: str = typer.Option(..., "--once", help="Single request for one team job"),
    case_id: str | None = typer.Option(None, "--case-id", help="Optional existing case id"),
    job_id: str | None = typer.Option(None, "--job-id", help="Optional explicit job id"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model"),
    hf_model_id: str | None = typer.Option(None, "--hf-model-id", help="Override HF model id"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    ensure_artifact_scaffold()
    parsed = _load_team_spec(spec)

    config, _source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    _require_permission_or_exit(config, "runtime.run")
    orchestrator = _build_orchestrator(
        config=config,
        provider_name=config.llm_provider,
        fallback_provider=config.fallback_provider,
    )
    startup_error = _startup_abort(
        config,
        getattr(orchestrator, "governance_runtime", None),
    )
    if startup_error:
        typer.echo(f"POLICY_UNAVAILABLE: {startup_error}")
        raise typer.Exit(code=2)
    if not config.team.enabled:
        typer.echo("Team runtime disabled in runtime config.")
        raise typer.Exit(code=2)

    supervisor = TeamSupervisor(orchestrator=orchestrator, config=config)
    result = supervisor.run(spec=parsed, request=once, case_id=case_id, job_id=job_id)
    payload = _with_contract_version(
        {
            "job": result.job.model_dump(mode="json"),
            "tasks": [item.model_dump(mode="json") for item in result.tasks],
            "handoff_count": len(result.handoffs),
            "event_count": len(result.events),
            "audit_envelope_path": result.audit_envelope_path,
        }
    )
    write_artifact("team_summary", payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(result.job.final_output or "")


@team_app.command("resume")
def team_resume(
    spec: str = typer.Option(..., "--spec", help="Team spec path"),
    job_id: str = typer.Option(..., "--job-id", help="Blocked/escalated source job id"),
    root_dir: str = typer.Option(
        ".binliquid/team/jobs",
        "--root-dir",
        help="Source and destination team artifact root directory",
    ),
    resume_job_id: str | None = typer.Option(
        None,
        "--resume-job-id",
        help="Optional explicit resume job id",
    ),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model"),
    hf_model_id: str | None = typer.Option(None, "--hf-model-id", help="Override HF model id"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    ensure_artifact_scaffold()
    parsed = _load_team_spec(spec)

    try:
        source_status = load_job_status(job_id, root_dir=root_dir)
        source_events = load_events(job_id, root_dir=root_dir)
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps(
                {"status": "error", "error": str(exc), "job_id": job_id, "root_dir": root_dir},
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1) from None

    source_job = source_status.get("job", {})
    source_request = str(source_job.get("request") or "").strip()
    source_case_id = str(source_job.get("case_id") or "").strip()
    if not source_request or not source_case_id:
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "error": "source job status missing request/case_id",
                    "job_id": job_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    config, _source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    _require_permission_or_exit(config, "runtime.resume")
    config = config.model_copy(
        update={"team": config.team.model_copy(update={"artifact_dir": root_dir})}
    )

    orchestrator = _build_orchestrator(
        config=config,
        provider_name=config.llm_provider,
        fallback_provider=config.fallback_provider,
    )
    startup_error = _startup_abort(
        config,
        getattr(orchestrator, "governance_runtime", None),
    )
    if startup_error:
        typer.echo(f"POLICY_UNAVAILABLE: {startup_error}")
        raise typer.Exit(code=2)
    if not config.team.enabled:
        typer.echo("Team runtime disabled in runtime config.")
        raise typer.Exit(code=2)

    governance_runtime = getattr(orchestrator, "governance_runtime", None)
    overrides, resolved = _collect_resume_overrides(
        events=source_events,
        governance_runtime=governance_runtime,
    )
    if not overrides:
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "error": "no executed approvals found for resume",
                    "job_id": job_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1)

    try:
        continuation_state = derive_resume_continuation_state(
            spec=parsed,
            source_job_id=job_id,
            root_dir=root_dir,
            source_status=source_status,
            source_events=source_events,
        )
    except ResumeContinuationError as exc:
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "error_code": exc.code,
                    "error": str(exc),
                    "job_id": job_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1) from None

    generated_resume_job_id = resume_job_id or (
        f"{job_id}-resume-{datetime.now(UTC).strftime('%H%M%S')}"
    )
    supervisor = TeamSupervisor(orchestrator=orchestrator, config=config)
    result = supervisor.run(
        spec=parsed,
        request=source_request,
        case_id=source_case_id,
        job_id=generated_resume_job_id,
        approval_overrides=overrides,
        continuation_state=continuation_state,
    )

    payload = _with_contract_version(
        {
            "status": "ok",
            "resumed_from_job_id": job_id,
            "job": result.job.model_dump(mode="json"),
            "tasks": [item.model_dump(mode="json") for item in result.tasks],
            "handoff_count": len(result.handoffs),
            "event_count": len(result.events),
            "resolved_approvals": resolved,
            "resume_outcomes": result.resume_outcomes,
            "audit_envelope_path": result.audit_envelope_path,
        }
    )
    write_artifact("team_summary", payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(result.job.final_output or "")


@team_app.command("status")
def team_status(
    job_id: str = typer.Option(..., "--job-id", help="Job id"),
    root_dir: str = typer.Option(
        ".binliquid/team/jobs",
        "--root-dir",
        help="Team artifact root directory",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    try:
        payload = _with_contract_version(load_job_status(job_id, root_dir=root_dir))
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps({"status": "error", "error": str(exc), "job_id": job_id}, indent=2)
        )
        raise typer.Exit(code=1) from None

    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        job = payload.get("job", {})
        typer.echo(
            f"job_id={job.get('job_id')} status={job.get('status')} "
            f"team_id={job.get('team_id')} case_id={job.get('case_id')}"
        )


@team_app.command("logs")
def team_logs(
    job_id: str = typer.Option(..., "--job-id", help="Job id"),
    root_dir: str = typer.Option(
        ".binliquid/team/jobs",
        "--root-dir",
        help="Team artifact root directory",
    ),
    json_stream: bool = typer.Option(True, "--json-stream/--no-json-stream", help="Emit JSONL"),
) -> None:
    events = load_events(job_id, root_dir=root_dir)
    if json_stream:
        for item in events:
            typer.echo(json.dumps(item, ensure_ascii=False))
        return
    typer.echo(json.dumps({"job_id": job_id, "events": events}, ensure_ascii=False, indent=2))


@team_app.command("replay")
def team_replay(
    job_id: str = typer.Option(..., "--job-id", help="Job id"),
    root_dir: str = typer.Option(
        ".binliquid/team/jobs",
        "--root-dir",
        help="Team artifact root directory",
    ),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Run replay consistency checks"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    try:
        payload = _with_contract_version(replay_job(job_id, root_dir=root_dir, verify=verify))
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps({"status": "error", "error": str(exc), "job_id": job_id}, indent=2)
        )
        raise typer.Exit(code=1) from None
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(
            f"job_id={payload.get('job_id')} status={payload.get('status')} "
            f"event_count={payload.get('event_count')}"
        )


@team_app.command("artifacts")
def team_artifacts(
    job_id: str = typer.Option(..., "--job-id", help="Job id"),
    export: str = typer.Option(..., "--export", help="Export directory"),
    root_dir: str = typer.Option(
        ".binliquid/team/jobs",
        "--root-dir",
        help="Team artifact root directory",
    ),
) -> None:
    source = Path(root_dir) / job_id
    if not source.exists():
        typer.echo(json.dumps({"status": "error", "error": "job not found", "job_id": job_id}))
        raise typer.Exit(code=1)

    destination = Path(export)
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for item in source.iterdir():
        if item.is_file():
            target = destination / item.name
            shutil.copy2(item, target)
            copied.append(str(target))
    typer.echo(
        json.dumps(
            _with_contract_version(
                {
                    "status": "ok",
                    "job_id": job_id,
                    "export_dir": str(destination),
                    "files": copied,
                }
            ),
            ensure_ascii=False,
            indent=2,
        )
    )


@team_app.command("pilot-check")
def team_pilot_check(
    spec: str = typer.Option(..., "--spec", help="Restricted pilot smoke spec path"),
    profile: str = typer.Option("restricted", "--profile", help="Runtime profile"),
    mode: str = typer.Option(
        "deterministic",
        "--mode",
        help="Pilot gate mode: deterministic|live-provider",
    ),
    root_dir: str = typer.Option(
        ".binliquid/team/pilot",
        "--root-dir",
        help="Pilot gate artifact root directory",
    ),
    report: str = typer.Option(
        "artifacts/team_pilot_report.json",
        "--report",
        help="Pilot gate report output path",
    ),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model"),
    hf_model_id: str | None = typer.Option(None, "--hf-model-id", help="Override HF model id"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    ensure_artifact_scaffold()
    parsed = _load_team_spec(spec)
    config, _source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    _require_permission_or_exit(config, "runtime.run")
    if not config.team.enabled:
        typer.echo("Team runtime disabled in runtime config.")
        raise typer.Exit(code=2)

    runtime = _build_governance_runtime(config)
    startup_error = _startup_abort(config, runtime)
    if startup_error:
        typer.echo(f"POLICY_UNAVAILABLE: {startup_error}")
        raise typer.Exit(code=2)

    live_builder = None
    if mode.strip().lower() == "live-provider":
        def _live_builder(runtime_config: RuntimeConfig):
            return _build_orchestrator(
                runtime_config,
                provider_name=runtime_config.llm_provider,
                fallback_provider=runtime_config.fallback_provider,
            )

        live_builder = _live_builder

    try:
        payload = run_pilot_check(
            spec=parsed,
            config=config,
            mode=mode,
            root_dir=root_dir,
            live_orchestrator_builder=live_builder,
        )
    except Exception as exc:  # noqa: BLE001
        error_code = getattr(exc, "error_code", "PILOT_CHECK_FAILED")
        exit_code = 2 if error_code in {"INVALID_INPUT", "TEAM_SPEC_INVALID"} else 1
        typer.echo(
            json.dumps(
                {
                    "status": "error",
                    "error_code": error_code,
                    "error": str(exc),
                    "spec": spec,
                    "mode": mode,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=exit_code) from None

    payload.setdefault("artifacts", {})["report_path"] = write_pilot_report(
        report,
        payload,
        config=config,
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        counters = payload.get("counters", {})
        checks = payload.get("checks", {})
        replay_status = (
            "ok"
            if checks.get("replay_integrity", {}).get("status") == "pass"
            else "fail"
        )
        tamper_status = (
            "fail"
            if counters.get("tamper_verify_unexpected_pass_count", 0) == 0
            else "unexpected-pass"
        )
        reuse_status = (
            "blocked"
            if counters.get("approval_reuse_unexpected_success_count", 0) == 0
            else "reused"
        )
        scope_status = (
            "blocked"
            if counters.get("scope_violation_unexpected_success_count", 0) == 0
            else "bypassed"
        )
        bounded_status = payload.get("bounded_concurrency_status", "unknown")
        typer.echo(
            f"{payload.get('overall_status', 'fail').upper()} "
            f"profile={payload.get('profile')} mode={payload.get('mode')} "
            f"jobs={len(payload.get('job_ids', []))} events={counters.get('total_events', 0)} "
            f"approvals={counters.get('approvals_created', 0)}/"
            f"{counters.get('approvals_approved', 0)}/"
            f"{counters.get('approvals_executed', 0)}/"
            f"{counters.get('approvals_consumed', 0)} "
            f"replay={replay_status} tamper={tamper_status} "
            f"reuse={reuse_status} scope={scope_status} bounded={bounded_status}"
        )
    if payload.get("overall_status") != "pass":
        raise typer.Exit(code=1)


@auth_app.command("whoami")
def auth_whoami(
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    payload = _with_contract_version(describe_actor(config))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        actor_id = payload.get("actor", {}).get("actor_id") if payload.get("verified") else None
        typer.echo(actor_id or "unverified")
    if not payload.get("verified"):
        raise typer.Exit(code=1)


@auth_app.command("check")
def auth_check(
    permission: str = typer.Option(..., "--permission", help="Permission to validate"),
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    payload = _with_contract_version(check_permission(config, permission=permission))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"allowed={payload['allowed']}")
    if not payload.get("allowed"):
        raise typer.Exit(code=1)


@security_app.command("baseline")
def security_baseline(
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    ensure_artifact_scaffold()
    config = RuntimeConfig.from_profile(profile)
    payload = _with_contract_version(security_posture(config))
    write_signed_json(
        path="artifacts/security_posture.json",
        artifact="security_posture",
        data=payload,
        config=config,
        purpose="security-posture",
        status="ok" if payload.get("overall_status") == "pass" else "error",
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload.get("overall_status", "fail"))
    if payload.get("overall_status") != "pass":
        raise typer.Exit(code=1)


@keys_app.command("status")
def keys_status_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    payload = _with_contract_version(key_status(RuntimeConfig.from_profile(profile)))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"provider={payload['provider']} current_key_id={payload['current_key_id']}")


@keys_app.command("verify")
def keys_verify_cmd(
    path: str = typer.Option(..., "--path", help="Signed artifact path"),
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    payload = _with_contract_version(
        verify_signed_artifact(path=path, config=RuntimeConfig.from_profile(profile))
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"verified={payload.get('verified')}")
    if not payload.get("verified"):
        raise typer.Exit(code=1)


@keys_app.command("rotate-plan")
def keys_rotate_plan_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    next_key_id: str | None = typer.Option(None, "--next-key-id", help="Planned next key id"),
    activate_at: str | None = typer.Option(None, "--activate-at", help="Planned activation time"),
    retire_after: str | None = typer.Option(None, "--retire-after", help="Planned retirement time"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    payload = _with_contract_version(
        rotate_plan(
            RuntimeConfig.from_profile(profile),
            next_key_id=next_key_id,
            activate_at=activate_at,
            retire_after=retire_after,
        )
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"next_key_id={payload['next_key_id']}")


@migrate_app.command("plan")
def migrate_plan_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    payload = _with_contract_version(migration_plan(RuntimeConfig.from_profile(profile)))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["compatible_upgrade_path"])


@migrate_app.command("apply")
def migrate_apply_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Preview only"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    _require_permission_or_exit(config, "maintenance.enter")
    payload = _with_contract_version(migration_apply(config, dry_run=dry_run))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["status"])


@backup_app.command("create")
def backup_create_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    output_dir: str | None = typer.Option(None, "--output-dir", help="Backup output directory"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    _require_permission_or_exit(config, "backup.create")
    payload = _with_contract_version(create_backup(config, output_dir=output_dir))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["backup_dir"])


@backup_app.command("verify")
def backup_verify_cmd(
    backup_dir: str = typer.Option(..., "--backup-dir", help="Backup directory"),
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    payload = _with_contract_version(
        restore_verify(RuntimeConfig.from_profile(profile), backup_dir=backup_dir)
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"verified={payload['verified']}")
    if not payload.get("verified"):
        raise typer.Exit(code=1)


@restore_app.command("verify")
def restore_verify_cmd(
    backup_dir: str = typer.Option(..., "--backup-dir", help="Backup directory to validate"),
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    _require_permission_or_exit(config, "restore.verify")
    payload = _with_contract_version(restore_verify(config, backup_dir=backup_dir))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"verified={payload['verified']}")
    if not payload.get("verified"):
        raise typer.Exit(code=1)


@support_bundle_app.command("export")
def support_bundle_export_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    output: str | None = typer.Option(None, "--output", help="Optional zip output path"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    _require_permission_or_exit(config, "support.export")
    payload = _with_contract_version(export_support_bundle(config, output_path=output))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["archive_path"])


@metrics_app.command("snapshot")
def metrics_snapshot_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    ensure_artifact_scaffold()
    config = RuntimeConfig.from_profile(profile)
    payload = _with_contract_version(collect_metrics_snapshot(config))
    write_signed_json(
        path="artifacts/metrics_snapshot.json",
        artifact="metrics_snapshot",
        data=payload,
        config=config,
        purpose="metrics-snapshot",
    )
    if config.observability.file_snapshot_enabled:
        from binliquid.enterprise.observability import write_prometheus_textfile

        write_prometheus_textfile(payload, config.observability.prometheus_textfile_path)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["generated_at"])


@ga_app.command("readiness")
def ga_readiness_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    report: str = typer.Option(
        "artifacts/ga_readiness_report.json",
        "--report",
        help="GA readiness report output path",
    ),
    qualification_report: str = typer.Option(
        "artifacts/qualification_report.json",
        "--qualification-report",
        help="Qualification evidence report path",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    ensure_artifact_scaffold()
    config = RuntimeConfig.from_profile(profile)
    payload = _with_contract_version(
        ga_readiness_report(config, qualification_report_path=qualification_report)
    )
    write_signed_json(
        path=report,
        artifact="ga_readiness_report",
        data=payload,
        config=config,
        purpose="ga-readiness",
        status="ok" if payload.get("overall_status") != "red" else "error",
    )
    markdown_path = Path(report).with_name("GA_READINESS_REPORT.md")
    markdown_path.write_text(render_ga_readiness_markdown(payload), encoding="utf-8")
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["overall_status"])
    if payload.get("overall_status") == "red":
        raise typer.Exit(code=1)


@qualification_app.command("run")
def qualification_run_cmd(
    profile: str = typer.Option("enterprise", help="Config profile"),
    mode: str = typer.Option("mixed", help="Qualification evidence mode"),
    soak_hours: float = typer.Option(
        6.0,
        "--soak-hours",
        help="Requested soak duration in hours for the 6h qualification workload.",
    ),
    output_root: str = typer.Option(
        "artifacts/qualification",
        "--output-root",
        help="Qualification output root directory",
    ),
    workloads: str | None = typer.Option(
        None,
        "--workloads",
        help="Comma-separated qualification workloads to run",
    ),
    merge_from_report: str | None = typer.Option(
        None,
        "--merge-from-report",
        help="Existing signed qualification report to merge subset reruns into",
    ),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    resolved, _source_map = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=resolved.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        _code, message = validation_error
        typer.echo(message)
        raise typer.Exit(code=1)

    for permission in (
        "runtime.run",
        "approval.decide",
        "approval.execute",
        "support.export",
        "backup.create",
        "restore.verify",
    ):
        _require_permission_or_exit(resolved, permission)

    try:
        selected_workloads = None
        if workloads is not None:
            selected_workloads = [
                item.strip()
                for item in workloads.split(",")
                if item.strip()
            ]
        payload = run_qualification(
            config=resolved,
            mode=mode,
            soak_hours=soak_hours,
            output_root=output_root,
            workloads=selected_workloads,
            merge_from_report=merge_from_report,
            live_orchestrator_builder=lambda runtime_config: _build_orchestrator(
                runtime_config,
                provider_name=resolved.llm_provider,
                fallback_provider=resolved.fallback_provider,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        error_code = getattr(exc, "error_code", "QUALIFICATION_FAILED")
        payload = _with_contract_version(
            {
                "status": "error",
                "error_code": error_code,
                "error": str(exc),
            }
        )
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(f"{error_code}: {exc}")
        raise typer.Exit(code=2) from None

    payload = _with_contract_version(payload)
    paths = write_qualification_report(payload=payload, config=resolved, output_root=output_root)
    payload.setdefault("artifacts", {})
    payload["artifacts"].update(paths)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload.get("go_no_go", "conditional"))
    if payload.get("go_no_go") == "no-go":
        raise typer.Exit(code=1)


@benchmark_app.command("smoke")
def benchmark_smoke(
    profile: str = typer.Option("lite", help="Config profile"),
    mode: str = typer.Option("all", help="A|B|C|D|both|all"),
    suite: str = typer.Option("smoke", help="smoke|quality"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    task_limit: int | None = typer.Option(None, help="Limit number of benchmark tasks"),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
) -> None:
    ensure_artifact_scaffold()
    resolved, _ = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=resolved.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        _code, message = validation_error
        typer.echo(message)
        raise typer.Exit(code=1)

    result = run_smoke_benchmark(
        profile=profile,
        mode=mode,
        suite=suite,
        output_path=output,
        task_limit=task_limit,
        provider=resolved.llm_provider,
        fallback_provider=resolved.fallback_provider,
        model=resolved.model_name,
        hf_model_id=resolved.hf_model_id,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    write_artifact("benchmark_summary", {"kind": "smoke", "result": result})


@benchmark_app.command("team")
def benchmark_team(
    profile: str = typer.Option("balanced", help="Config profile"),
    suite: str = typer.Option("smoke", help="smoke|quality"),
    spec: str = typer.Option("team.yaml", "--spec", help="Team spec path"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    task_limit: int | None = typer.Option(None, help="Limit number of benchmark tasks"),
    deterministic_mock: bool = typer.Option(
        False,
        "--deterministic-mock",
        help="Use deterministic mock orchestrator (CI-friendly).",
    ),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
) -> None:
    ensure_artifact_scaffold()
    resolved, _ = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=resolved.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        _code, message = validation_error
        typer.echo(message)
        raise typer.Exit(code=1)

    result = run_team_benchmark(
        profile=profile,
        suite=suite,
        spec_path=spec,
        output_path=output,
        task_limit=task_limit,
        provider=resolved.llm_provider,
        fallback_provider=resolved.fallback_provider,
        model=resolved.model_name,
        hf_model_id=resolved.hf_model_id,
        deterministic_mock=deterministic_mock,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    write_artifact("benchmark_summary", {"kind": "team", "result": result})


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
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
) -> None:
    ensure_artifact_scaffold()
    resolved, _ = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=resolved.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        _code, message = validation_error
        typer.echo(message)
        raise typer.Exit(code=1)

    result = run_ablation_benchmark(
        profile=profile,
        mode=mode,
        output_path=output,
        report_path=report,
        task_limit=task_limit,
        suite=suite,
        provider=resolved.llm_provider,
        fallback_provider=resolved.fallback_provider,
        model=resolved.model_name,
        hf_model_id=resolved.hf_model_id,
    )
    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    write_artifact("benchmark_summary", {"kind": "ablation", "result": result})


@benchmark_app.command("energy")
def benchmark_energy(
    profile: str = typer.Option("balanced", help="Config profile"),
    energy_mode: str = typer.Option("measured", help="measured|estimated"),
    output: str | None = typer.Option(None, help="Output JSON path"),
    task_limit: int | None = typer.Option(2, help="Limit number of benchmark tasks"),
    provider: str | None = typer.Option(
        None,
        help="Override provider (energy runs smoke mode-A workload with this provider).",
    ),
    fallback_provider: str | None = typer.Option(
        None,
        help="Override fallback provider for mode-A workload execution.",
    ),
    model: str | None = typer.Option(None, "--model", help="Override model name"),
    hf_model_id: str | None = typer.Option(
        None,
        "--hf-model-id",
        help="Override transformers model id",
    ),
) -> None:
    ensure_artifact_scaffold()
    resolved, _ = resolve_runtime_config(
        profile=profile,
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    validation_error = _validate_model_override_combo(
        effective_provider=resolved.llm_provider,
        model_override=model,
        hf_model_id_override=hf_model_id,
    )
    if validation_error is not None:
        _code, message = validation_error
        typer.echo(message)
        raise typer.Exit(code=1)

    result = run_energy_benchmark(
        profile=profile,
        energy_mode=energy_mode,
        task_limit=task_limit,
        output_path=output,
        provider=resolved.llm_provider,
        fallback_provider=resolved.fallback_provider,
        model=resolved.model_name,
        hf_model_id=resolved.hf_model_id,
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
