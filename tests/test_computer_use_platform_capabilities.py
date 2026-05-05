from __future__ import annotations

from binliquid.computer_use.vision_runtime.platforms import (
    ComputerUsePlatform,
    build_platform_capabilities,
)
from binliquid.runtime.config import ComputerUseRuntimeConfig


def test_default_config_reports_all_platforms_fail_closed() -> None:
    capabilities = build_platform_capabilities(ComputerUseRuntimeConfig())

    assert set(capabilities) == {"macos", "windows", "linux"}
    for platform, capability in capabilities.items():
        assert capability.platform == platform
        assert capability.stage == "not_qualified"
        assert capability.live_enabled is False
        assert capability.execution_modes == ["dry_run", "step_approval"]
        assert capability.replayable is True
        assert capability.fail_closed is True

    assert capabilities["macos"].reason_code == "MACOS_COMPUTER_USE_NOT_QUALIFIED"
    assert capabilities["windows"].reason_code == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    assert capabilities["linux"].reason_code == "LINUX_COMPUTER_USE_NOT_QUALIFIED"


def test_platform_capability_serializes_with_operator_contract_aliases() -> None:
    capability = build_platform_capabilities(ComputerUseRuntimeConfig())[
        ComputerUsePlatform.WINDOWS.value
    ]
    payload = capability.model_dump(mode="json", by_alias=True)

    assert payload["liveEnabled"] is False
    assert payload["captureBackend"] == "disabled"
    assert payload["inputBackend"] == "disabled"
    assert payload["reasonCode"] == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    assert payload["failClosed"] is True
