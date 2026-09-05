"""Disabled legacy wire fields; no optional extension discovery or driver imports."""

from typing import Any

from imperaos.contracts.operator_panel import (
    ComputerUseCapabilityContract,
    ComputerUseVisionRuntimeCapabilityContract,
)


def retired_computer_use_capabilities(platform: str) -> tuple[dict[str, Any], dict[str, Any]]:
    platform = platform if platform in {"macos", "windows", "linux"} else "unknown"
    reason = "COMPUTER_USE_EXTENSION_NOT_INSTALLED"
    summary = "Computer use is a paused optional extension, outside the core product."
    common = {
        "enabled": False,
        "stage": "not_qualified",
        "platform": platform,
        "executionModes": [],
        "replayable": True,
        "failClosed": True,
        "reasonCode": reason,
        "summary": summary,
    }
    pilot = ComputerUseCapabilityContract.model_validate(
        {
            **common,
            "scope": "optional_extension",
            "adapterStatus": "not_installed",
        }
    )
    vision = ComputerUseVisionRuntimeCapabilityContract.model_validate(
        {
            **common,
            "scope": "vision_first_desktop_web_file",
            "provider": {"kind": "none", "name": "none", "configured": False, "model": None},
            "safety": {
                "rawScreenshotPersistence": False,
                "rawScreenshotRetention": "disabled",
                "rawScreenshotMaxCount": 0,
                "terminalControl": "deny",
                "sensitiveSurfacePolicy": "stop",
                "approvalRequiredForRiskyActions": True,
            },
            "platforms": {
                name: {
                    "platform": name,
                    "stage": "not_qualified",
                    "liveEnabled": False,
                    "captureBackend": "disabled",
                    "inputBackend": "disabled",
                    "provider": "none",
                    "executionModes": [],
                    "replayable": True,
                    "failClosed": True,
                    "reasonCode": reason,
                    "summary": summary,
                    "blockers": [reason],
                }
                for name in ("macos", "windows", "linux")
            },
            "capabilityResolution": {
                "platform": platform,
                "status": "blocked",
                "reasonCode": reason,
                "blockers": [reason],
                "evidence": {"status": "not_applicable"},
                "config": {},
                "driver": {},
                "safety": {},
            },
        }
    )
    return pilot.model_dump(mode="json", by_alias=True), vision.model_dump(
        mode="json", by_alias=True
    )
