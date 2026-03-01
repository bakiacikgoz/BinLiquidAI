from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expert_timeout_ms: int = Field(default=2500, ge=1)
    max_retries: int = Field(default=1, ge=0)
    circuit_breaker_threshold: int = Field(default=3, ge=1)
    circuit_breaker_cooldown_s: int = Field(default=300, ge=1)
    llm_timeout_ms: int = Field(default=60000, ge=1000)
    max_tool_calls: int = Field(default=4, ge=1)
    max_recursion_depth: int = Field(default=3, ge=1)


class SLTCConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    enabled: bool = False
    decay: float = Field(default=0.82, ge=0.0, le=1.0)
    spike_threshold: float = Field(default=0.55, ge=0.0, le=2.0)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    db_path: str = ".binliquid/memory.sqlite3"
    salience_threshold: float = Field(default=0.62, ge=0.0, le=1.0)
    salience_decay: float = Field(default=0.82, ge=0.0, le=1.0)
    max_rows: int = Field(default=5000, ge=100)
    context_top_k: int = Field(default=4, ge=0)


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    model_name: str = "lfm2.5-thinking:1.2b"
    profile_name: str = "default"
    llm_provider: str = "auto"
    fallback_provider: str = "transformers"
    fallback_enabled: bool = True
    hf_model_id: str = "distilgpt2"
    device: str = "cpu"
    router_mode: str = "rule"
    shadow_router_enabled: bool = False
    shadow_router_mode: str = "sltc"
    planner_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    answer_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    router_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    latency_budget_ms: int = Field(default=4000, ge=1)
    debug_mode: bool = False
    privacy_mode: bool = True
    enable_persistent_memory: bool = False
    memory_ttl_days: int = Field(default=30, ge=1)
    fast_path_regret_window: int = Field(default=2, ge=1, le=10)
    fast_path_regret_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    env_prefix: str = "BINLIQUID"
    web_enabled: bool = False
    workspace_root: str = "."
    trace_dir: str = ".binliquid/traces"
    router_dataset_path: str = ".binliquid/research/router_dataset.jsonl"
    limits: RuntimeLimits = Field(default_factory=RuntimeLimits)
    sltc: SLTCConfig = Field(default_factory=SLTCConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    @classmethod
    def from_profile(cls, profile: str = "default", root_dir: Path | None = None) -> RuntimeConfig:
        resolved, _sources = resolve_runtime_config(profile=profile, root_dir=root_dir)
        return resolved

    @classmethod
    def from_toml(cls, path: str | Path) -> RuntimeConfig:
        config_path = Path(path)
        with config_path.open("rb") as file_obj:
            data = tomllib.load(file_obj)

        app_data = data.get("app", {})
        limits_data = data.get("limits", {})
        sltc_data = data.get("sltc", {})
        memory_data = data.get("memory", {})
        return cls(
            model_name=app_data.get("model_name", "lfm2.5-thinking:1.2b"),
            profile_name=app_data.get("profile_name", "default"),
            llm_provider=app_data.get("llm_provider", "auto"),
            fallback_provider=app_data.get("fallback_provider", "transformers"),
            fallback_enabled=app_data.get("fallback_enabled", True),
            hf_model_id=app_data.get("hf_model_id", "distilgpt2"),
            device=app_data.get("device", "cpu"),
            router_mode=app_data.get("router_mode", "rule"),
            shadow_router_enabled=app_data.get("shadow_router_enabled", False),
            shadow_router_mode=app_data.get("shadow_router_mode", "sltc"),
            planner_temperature=app_data.get("planner_temperature", 0.0),
            answer_temperature=app_data.get("answer_temperature", 0.2),
            router_confidence_threshold=app_data.get("router_confidence_threshold", 0.6),
            latency_budget_ms=app_data.get("latency_budget_ms", 4000),
            debug_mode=app_data.get("debug_mode", False),
            privacy_mode=app_data.get("privacy_mode", True),
            enable_persistent_memory=app_data.get("enable_persistent_memory", False),
            memory_ttl_days=app_data.get("memory_ttl_days", 30),
            fast_path_regret_window=app_data.get("fast_path_regret_window", 2),
            fast_path_regret_threshold=app_data.get("fast_path_regret_threshold", 0.2),
            env_prefix=app_data.get("env_prefix", "BINLIQUID"),
            web_enabled=app_data.get("web_enabled", False),
            workspace_root=app_data.get("workspace_root", "."),
            trace_dir=app_data.get("trace_dir", ".binliquid/traces"),
            router_dataset_path=app_data.get(
                "router_dataset_path",
                ".binliquid/research/router_dataset.jsonl",
            ),
            limits=RuntimeLimits(
                expert_timeout_ms=limits_data.get("expert_timeout_ms", 2500),
                max_retries=limits_data.get("max_retries", 1),
                circuit_breaker_threshold=limits_data.get("circuit_breaker_threshold", 3),
                circuit_breaker_cooldown_s=limits_data.get("circuit_breaker_cooldown_s", 300),
                llm_timeout_ms=limits_data.get("llm_timeout_ms", 60000),
                max_tool_calls=limits_data.get("max_tool_calls", 4),
                max_recursion_depth=limits_data.get("max_recursion_depth", 3),
            ),
            sltc=SLTCConfig(
                enabled=sltc_data.get("enabled", False),
                decay=sltc_data.get("decay", 0.82),
                spike_threshold=sltc_data.get("spike_threshold", 0.55),
                confidence_threshold=sltc_data.get("confidence_threshold", 0.6),
            ),
            memory=MemoryConfig(
                db_path=memory_data.get("db_path", ".binliquid/memory.sqlite3"),
                salience_threshold=memory_data.get("salience_threshold", 0.62),
                salience_decay=memory_data.get("salience_decay", 0.82),
                max_rows=memory_data.get("max_rows", 5000),
                context_top_k=memory_data.get("context_top_k", 4),
            ),
        )


ENV_PATHS: dict[str, str] = {
    "MODEL_NAME": "model_name",
    "PROFILE_NAME": "profile_name",
    "LLM_PROVIDER": "llm_provider",
    "FALLBACK_PROVIDER": "fallback_provider",
    "FALLBACK_ENABLED": "fallback_enabled",
    "HF_MODEL_ID": "hf_model_id",
    "DEVICE": "device",
    "ROUTER_MODE": "router_mode",
    "SHADOW_ROUTER_ENABLED": "shadow_router_enabled",
    "SHADOW_ROUTER_MODE": "shadow_router_mode",
    "PLANNER_TEMPERATURE": "planner_temperature",
    "ANSWER_TEMPERATURE": "answer_temperature",
    "ROUTER_CONFIDENCE_THRESHOLD": "router_confidence_threshold",
    "LATENCY_BUDGET_MS": "latency_budget_ms",
    "DEBUG_MODE": "debug_mode",
    "PRIVACY_MODE": "privacy_mode",
    "ENABLE_PERSISTENT_MEMORY": "enable_persistent_memory",
    "MEMORY_TTL_DAYS": "memory_ttl_days",
    "FAST_PATH_REGRET_WINDOW": "fast_path_regret_window",
    "FAST_PATH_REGRET_THRESHOLD": "fast_path_regret_threshold",
    "WEB_ENABLED": "web_enabled",
    "WORKSPACE_ROOT": "workspace_root",
    "TRACE_DIR": "trace_dir",
    "ROUTER_DATASET_PATH": "router_dataset_path",
    "LIMITS_EXPERT_TIMEOUT_MS": "limits.expert_timeout_ms",
    "LIMITS_MAX_RETRIES": "limits.max_retries",
    "LIMITS_CIRCUIT_BREAKER_THRESHOLD": "limits.circuit_breaker_threshold",
    "LIMITS_CIRCUIT_BREAKER_COOLDOWN_S": "limits.circuit_breaker_cooldown_s",
    "LIMITS_LLM_TIMEOUT_MS": "limits.llm_timeout_ms",
    "LIMITS_MAX_TOOL_CALLS": "limits.max_tool_calls",
    "LIMITS_MAX_RECURSION_DEPTH": "limits.max_recursion_depth",
    "SLTC_ENABLED": "sltc.enabled",
    "SLTC_DECAY": "sltc.decay",
    "SLTC_SPIKE_THRESHOLD": "sltc.spike_threshold",
    "SLTC_CONFIDENCE_THRESHOLD": "sltc.confidence_threshold",
    "MEMORY_DB_PATH": "memory.db_path",
    "MEMORY_SALIENCE_THRESHOLD": "memory.salience_threshold",
    "MEMORY_SALIENCE_DECAY": "memory.salience_decay",
    "MEMORY_MAX_ROWS": "memory.max_rows",
    "MEMORY_CONTEXT_TOP_K": "memory.context_top_k",
}


def resolve_runtime_config(
    *,
    profile: str = "default",
    root_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
) -> tuple[RuntimeConfig, dict[str, str]]:
    base = RuntimeConfig().model_dump(mode="python")
    source_map = _build_default_source_map(base)

    profile_payload = _load_profile_payload(profile=profile, root_dir=root_dir)
    _deep_merge(base, profile_payload, source="profile", source_map=source_map)

    env_payload = _build_env_payload(env=env, env_prefix=str(base.get("env_prefix", "BINLIQUID")))
    _deep_merge(base, env_payload, source="env", source_map=source_map)

    cli_payload = _build_cli_payload(cli_overrides or {})
    _deep_merge(base, cli_payload, source="cli", source_map=source_map)

    config = RuntimeConfig.model_validate(base)
    return config, source_map


def redact_config_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    redacted = _deep_copy_dict(payload)
    sensitive_markers = ("token", "secret", "password", "key")
    for path in _iter_leaf_paths(redacted):
        key = path.split(".")[-1].lower()
        if any(marker in key for marker in sensitive_markers):
            _set_in_dict(redacted, path, "***REDACTED***")
    return redacted


def _load_profile_payload(*, profile: str, root_dir: Path | None) -> dict[str, Any]:
    base_dir = root_dir or Path(__file__).resolve().parents[2]
    config_path = base_dir / "config" / f"{profile}.toml"
    with config_path.open("rb") as file_obj:
        data = tomllib.load(file_obj)

    app_data = dict(data.get("app", {}))
    app_data["profile_name"] = profile
    payload: dict[str, Any] = {
        **app_data,
        "limits": dict(data.get("limits", {})),
        "sltc": dict(data.get("sltc", {})),
        "memory": dict(data.get("memory", {})),
    }
    return payload


def _build_env_payload(*, env: Mapping[str, str] | None, env_prefix: str) -> dict[str, Any]:
    values = env or os.environ
    payload: dict[str, Any] = {}
    defaults = RuntimeConfig().model_dump(mode="python")
    prefix = f"{env_prefix}_"
    for env_key, path in ENV_PATHS.items():
        full_key = f"{prefix}{env_key}"
        if full_key not in values:
            continue
        raw_value = values[full_key]
        current = _get_from_dict(defaults, path)
        coerced = _coerce_value(raw_value, current)
        _set_in_dict(payload, path, coerced)
    return payload


def _build_cli_payload(cli_overrides: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in cli_overrides.items():
        if value is None:
            continue
        if key in {"source_map", "json"}:
            continue
        _set_in_dict(payload, key, value)
    return payload


def _build_default_source_map(payload: Mapping[str, Any]) -> dict[str, str]:
    return {path: "defaults" for path in _iter_leaf_paths(payload)}


def _iter_leaf_paths(payload: Mapping[str, Any], prefix: str = "") -> list[str]:
    result: list[str] = []
    for key in sorted(payload.keys()):
        path = f"{prefix}.{key}" if prefix else str(key)
        value = payload[key]
        if isinstance(value, Mapping):
            result.extend(_iter_leaf_paths(value, path))
        else:
            result.append(path)
    return result


def _deep_merge(
    target: dict[str, Any],
    update: Mapping[str, Any],
    *,
    source: str,
    source_map: dict[str, str],
    prefix: str = "",
) -> None:
    for key, value in update.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            existing = target.get(key)
            if not isinstance(existing, dict):
                existing = {}
                target[key] = existing
            _deep_merge(existing, value, source=source, source_map=source_map, prefix=path)
            continue
        target[key] = value
        source_map[path] = source


def _get_from_dict(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _set_in_dict(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        nxt = current.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            current[part] = nxt
        current = nxt
    current[parts[-1]] = value


def _coerce_value(raw: str, template: Any) -> Any:
    if isinstance(template, bool):
        lowered = raw.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
        raise ValueError(f"invalid bool env value: {raw}")
    if isinstance(template, int) and not isinstance(template, bool):
        return int(raw.strip())
    if isinstance(template, float):
        return float(raw.strip())
    return raw


def _deep_copy_dict(data: Mapping[str, Any]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, Mapping):
            copied[str(key)] = _deep_copy_dict(value)
        else:
            copied[str(key)] = value
    return copied
