from binliquid.runtime.config import RuntimeConfig


def test_runtime_config_loads_balanced_profile() -> None:
    cfg = RuntimeConfig.from_profile("balanced")

    assert cfg.profile_name == "balanced"
    assert cfg.router_mode == "rule"
    assert cfg.shadow_router_enabled is True
    assert cfg.shadow_router_mode == "sltc"
    assert cfg.sltc.enabled is True
    assert cfg.enable_persistent_memory is True


def test_runtime_config_exposes_llm_timeout() -> None:
    cfg = RuntimeConfig.from_profile("lite")

    assert cfg.limits.llm_timeout_ms >= 1000
