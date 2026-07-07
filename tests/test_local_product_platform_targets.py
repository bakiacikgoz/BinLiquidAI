from __future__ import annotations

from binliquid.local_product.targets import default_target_registry, parse_platform_target


def test_default_target_registry_marks_supported_and_experimental_targets() -> None:
    registry = {target.target_id: target for target in default_target_registry()}

    assert registry["windows-x64"].claim_level == "source_supported"
    assert registry["darwin-arm64"].required_evidence == ["local_readiness"]
    assert registry["windows-arm64"].experimental is True
    assert registry["windows-arm64"].claim_level == "not_claimed"


def test_parse_current_and_known_target() -> None:
    target = parse_platform_target("windows-x64")

    assert target.target_id == "windows-x64"
    assert target.os == "windows"
    assert target.arch == "x64"
