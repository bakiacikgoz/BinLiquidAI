from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from binliquid.computer_use.vision_runtime.capability_resolver import (
    resolve_computer_use_capabilities,
)
from binliquid.runtime.config import ComputerUseRuntimeConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = REPO_ROOT / "contracts" / "computer_use" / "fixtures"
NOW = datetime(2026, 5, 6, tzinfo=UTC)


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _enabled_macos_config() -> ComputerUseRuntimeConfig:
    return ComputerUseRuntimeConfig(
        runtime_mode="vision_first",
        vision_enabled=True,
        vision_provider="ollama",
        vision_model="llava",
        macos_live_enabled=True,
        macos_capture_backend="screencapture",
        macos_input_backend="quartz",
        macos_require_step_approval=True,
    )


def test_missing_evidence_blocks_every_platform_with_preserved_reason_codes() -> None:
    resolution = resolve_computer_use_capabilities(
        config=ComputerUseRuntimeConfig(),
        profile="balanced",
        current_platform="windows",
        current_commit="fixture-commit",
        now=NOW,
    )

    assert resolution.artifact_version == "computer-use-capability-resolution/v1"
    assert resolution.status == "blocked"
    assert resolution.public_live_claim_allowed is False
    assert resolution.platforms["macos"].reason_code == "MACOS_COMPUTER_USE_NOT_QUALIFIED"
    assert resolution.platforms["windows"].reason_code == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    assert resolution.platforms["linux"].reason_code == "LINUX_COMPUTER_USE_NOT_QUALIFIED"
    assert resolution.platforms["macos"].live_enabled is False
    assert resolution.platforms["macos"].evidence.load_status == "missing"
    assert "COMPUTER_USE_EVIDENCE_MISSING" in resolution.platforms["macos"].blockers


def test_invalid_schema_evidence_blocks_fail_closed() -> None:
    payload = _fixture("macos_supervised_v2_evidence_pass.json")
    payload["unexpected"] = "not allowed"

    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={"macos": payload},
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.live_enabled is False
    assert macos.evidence.load_status == "invalid"
    assert "COMPUTER_USE_EVIDENCE_INVALID_SCHEMA" in macos.blockers


def test_stale_evidence_blocks_live_execution() -> None:
    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={
            "macos": _fixture("macos_supervised_v2_evidence_fail_stale.json")
        },
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.live_enabled is False
    assert "COMPUTER_USE_EVIDENCE_STALE" in macos.blockers


def test_commit_mismatch_blocks_live_execution() -> None:
    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={
            "macos": _fixture("macos_supervised_v2_evidence_fail_commit_mismatch.json")
        },
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.commit_match is False
    assert "COMPUTER_USE_EVIDENCE_COMMIT_MISMATCH" in macos.blockers


def test_raw_screenshot_fail_evidence_never_enables_live_execution() -> None:
    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={
            "macos": _fixture("macos_supervised_v2_evidence_fail_raw_screenshot.json")
        },
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "fail"
    assert macos.live_enabled is False
    assert macos.raw_screenshot_persistence_allowed is False
    assert "COMPUTER_USE_RAW_SCREENSHOT_INVARIANT_FAILED" in macos.blockers


def test_valid_macos_evidence_with_disabled_config_stays_blocked() -> None:
    resolution = resolve_computer_use_capabilities(
        config=ComputerUseRuntimeConfig(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={"macos": _fixture("macos_supervised_v2_evidence_pass.json")},
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.live_enabled is False
    assert macos.evidence.load_status == "valid"
    assert "COMPUTER_USE_CONFIG_LIVE_DISABLED" in macos.blockers


def test_valid_macos_evidence_on_windows_stays_blocked_for_local_runtime() -> None:
    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="windows",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={"macos": _fixture("macos_supervised_v2_evidence_pass.json")},
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.live_enabled is False
    assert "COMPUTER_USE_EVIDENCE_PLATFORM_MISMATCH" in macos.blockers


def test_valid_macos_evidence_with_supervised_config_allows_only_local_supervised_live() -> None:
    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={"macos": _fixture("macos_supervised_v2_evidence_pass.json")},
    )

    macos = resolution.platforms["macos"]
    assert resolution.status == "pass"
    assert resolution.public_live_claim_allowed is False
    assert macos.status == "pass"
    assert macos.live_enabled is True
    assert macos.public_live_claim_allowed is False
    assert "supervised_qualification" in macos.execution_modes
    assert "execute" not in macos.execution_modes
    assert macos.provider_match is True
    assert macos.backend_match is True
    assert macos.permission_checks_passed is True


def test_provider_and_backend_mismatch_block_even_with_pass_evidence() -> None:
    config = _enabled_macos_config().model_copy(
        update={
            "vision_provider": "mock",
            "vision_model": None,
            "macos_input_backend": "disabled",
        }
    )
    resolution = resolve_computer_use_capabilities(
        config=config,
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={"macos": _fixture("macos_supervised_v2_evidence_pass.json")},
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.provider_match is False
    assert macos.backend_match is False
    assert "COMPUTER_USE_EVIDENCE_PROVIDER_MISMATCH" in macos.blockers
    assert "COMPUTER_USE_EVIDENCE_BACKEND_MISMATCH" in macos.blockers


def test_driver_readiness_blocks_valid_evidence_when_driver_is_not_ready() -> None:
    resolution = resolve_computer_use_capabilities(
        config=_enabled_macos_config(),
        profile="balanced",
        current_platform="macos",
        current_commit="fixture-commit",
        now=NOW,
        evidence_by_platform={"macos": _fixture("macos_supervised_v2_evidence_pass.json")},
        driver_readiness_by_platform={
            "macos": {
                "platform": "macos",
                "live_execution_enabled": False,
                "reason_code": "MACOS_CAPTURE_BACKEND_UNAVAILABLE",
                "summary": "screencapture is not available",
            }
        },
    )

    macos = resolution.platforms["macos"]
    assert macos.status == "blocked"
    assert macos.live_enabled is False
    assert macos.driver_ready is False
    assert macos.driver_reason_code == "MACOS_CAPTURE_BACKEND_UNAVAILABLE"
    assert "MACOS_CAPTURE_BACKEND_UNAVAILABLE" in macos.blockers
