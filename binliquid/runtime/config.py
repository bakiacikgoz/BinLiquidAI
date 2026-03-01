from __future__ import annotations

import tomllib
from pathlib import Path

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
    planner_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    answer_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    router_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    latency_budget_ms: int = Field(default=4000, ge=1)
    debug_mode: bool = False
    privacy_mode: bool = True
    enable_persistent_memory: bool = False
    memory_ttl_days: int = Field(default=30, ge=1)
    web_enabled: bool = False
    workspace_root: str = "."
    trace_dir: str = ".binliquid/traces"
    router_dataset_path: str = ".binliquid/research/router_dataset.jsonl"
    limits: RuntimeLimits = Field(default_factory=RuntimeLimits)
    sltc: SLTCConfig = Field(default_factory=SLTCConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    @classmethod
    def from_profile(cls, profile: str = "default", root_dir: Path | None = None) -> RuntimeConfig:
        base_dir = root_dir or Path(__file__).resolve().parents[2]
        config_path = base_dir / "config" / f"{profile}.toml"
        return cls.from_toml(config_path)

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
            planner_temperature=app_data.get("planner_temperature", 0.0),
            answer_temperature=app_data.get("answer_temperature", 0.2),
            router_confidence_threshold=app_data.get("router_confidence_threshold", 0.6),
            latency_budget_ms=app_data.get("latency_budget_ms", 4000),
            debug_mode=app_data.get("debug_mode", False),
            privacy_mode=app_data.get("privacy_mode", True),
            enable_persistent_memory=app_data.get("enable_persistent_memory", False),
            memory_ttl_days=app_data.get("memory_ttl_days", 30),
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
