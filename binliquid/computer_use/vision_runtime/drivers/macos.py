from __future__ import annotations

from binliquid.computer_use.vision_runtime.drivers.base import PlatformDriverReadiness


def readiness(*, vision_enabled: bool) -> PlatformDriverReadiness:
    return PlatformDriverReadiness(
        platform="macos",
        live_execution_enabled=vision_enabled,
        reason_code=None if vision_enabled else "VISION_RUNTIME_NOT_CONFIGURED",
        summary=(
            "macOS vision-first runtime is configured for supervised execution."
            if vision_enabled
            else "macOS vision-first runtime is scaffolded but no vision provider is configured."
        ),
    )
