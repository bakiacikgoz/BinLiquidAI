from __future__ import annotations

from binliquid.runtime.config import redact_config_payload, resolve_runtime_config


def test_resolve_runtime_config_precedence_cli_wins_over_env_and_profile() -> None:
    env = {
        "BINLIQUID_LLM_PROVIDER": "ollama",
        "BINLIQUID_FALLBACK_PROVIDER": "transformers",
    }
    cfg, source_map = resolve_runtime_config(
        profile="lite",
        env=env,
        cli_overrides={"llm_provider": "transformers"},
    )

    assert cfg.llm_provider == "transformers"
    assert cfg.fallback_provider == "transformers"
    assert source_map["llm_provider"] == "cli"
    assert source_map["fallback_provider"] == "env"


def test_resolve_runtime_config_is_deterministic() -> None:
    env = {"BINLIQUID_ROUTER_MODE": "rule"}
    first, _ = resolve_runtime_config(profile="balanced", env=env)
    second, _ = resolve_runtime_config(profile="balanced", env=env)
    assert first.model_dump(mode="python") == second.model_dump(mode="python")


def test_redact_config_payload_masks_sensitive_keys() -> None:
    payload = {
        "llm_provider": "auto",
        "api_token": "secret-value",
        "nested": {"service_key": "k-123"},
    }
    redacted = redact_config_payload(payload)
    assert redacted["api_token"] == "***REDACTED***"
    assert redacted["nested"]["service_key"] == "***REDACTED***"
