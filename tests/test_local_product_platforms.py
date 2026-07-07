from __future__ import annotations

import pytest

from binliquid.local_product.platforms import (
    InvalidTargetFormatError,
    detect_current_target,
    parse_target,
)


def test_parse_supported_targets_with_claim_disabled_until_evidenced() -> None:
    target = parse_target("windows-x64")

    assert target.os == "windows"
    assert target.arch == "x64"
    assert target.target_id == "windows-x64"
    assert target.support_tier == "supported"
    assert target.claim_allowed is False
    assert target.reason_codes == ["EVIDENCE_REQUIRED_FOR_CLAIM"]


def test_parse_experimental_arm_targets_as_not_claimable() -> None:
    target = parse_target("linux-arm64")

    assert target.support_tier == "experimental"
    assert target.claim_allowed is False
    assert "EXPERIMENTAL_TARGET_REQUIRES_EVIDENCE" in target.reason_codes


def test_parse_unknown_arch_as_unsupported() -> None:
    target = parse_target("linux-riscv64")

    assert target.os == "linux"
    assert target.arch == "unknown"
    assert target.target_id == "linux-unknown"
    assert target.support_tier == "unsupported"
    assert target.claim_allowed is False
    assert "UNSUPPORTED_PLATFORM_TARGET" in target.reason_codes


def test_rejects_m4_as_platform_target() -> None:
    with pytest.raises(InvalidTargetFormatError):
        parse_target("m4")


def test_detect_current_target_supports_overrides() -> None:
    target = detect_current_target(system="Windows", machine="AMD64")

    assert target.target_id == "windows-x64"
    assert target.support_tier == "supported"

