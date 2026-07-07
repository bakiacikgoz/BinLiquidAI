from __future__ import annotations

import platform

from binliquid.local_product.models import PlatformTarget

SUPPORTED_TARGETS = ("darwin-arm64", "darwin-x64", "windows-x64", "linux-x64")
EXPERIMENTAL_TARGETS = ("windows-arm64", "linux-arm64")
MATRIX_TARGETS = (
    "darwin-arm64",
    "darwin-x64",
    "windows-x64",
    "linux-x64",
    "windows-arm64",
    "linux-arm64",
)


class InvalidTargetFormatError(ValueError):
    pass


class UnsupportedTargetError(ValueError):
    pass


def _normalize_os(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"darwin", "macos", "mac", "mac os x"}:
        return "darwin"
    if normalized in {"windows", "win32", "cygwin", "mingw"}:
        return "windows"
    if normalized in {"linux"}:
        return "linux"
    return "unknown"


def _normalize_arch(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"arm64", "aarch64"}:
        return "arm64"
    if normalized in {"x86_64", "amd64", "x64"}:
        return "x64"
    return "unknown"


def build_target(os_name: str, arch_name: str, *, evidenced: bool = False) -> PlatformTarget:
    os_value = _normalize_os(os_name)
    arch_value = _normalize_arch(arch_name)
    target_id = f"{os_value}-{arch_value}"
    reason_codes: list[str] = []
    support_tier = "unsupported"
    if target_id in SUPPORTED_TARGETS:
        support_tier = "supported"
        if not evidenced:
            reason_codes.append("EVIDENCE_REQUIRED_FOR_CLAIM")
    elif target_id in EXPERIMENTAL_TARGETS:
        support_tier = "experimental"
        reason_codes.append("EXPERIMENTAL_TARGET_REQUIRES_EVIDENCE")
    else:
        reason_codes.append("UNSUPPORTED_PLATFORM_TARGET")
    return PlatformTarget(
        os=os_value,
        arch=arch_value,
        targetId=target_id,
        supportTier=support_tier,
        claimAllowed=evidenced and support_tier == "supported",
        reasonCodes=[] if evidenced and support_tier == "supported" else reason_codes,
    )


def parse_target(value: str) -> PlatformTarget:
    normalized = value.strip().lower()
    if normalized == "auto":
        return detect_current_target()
    if normalized in {"m4", "macos-m4", "apple-m4"}:
        raise InvalidTargetFormatError("M4 is a device example, not a platform target")
    parts = normalized.split("-")
    if len(parts) != 2 or not all(parts):
        raise InvalidTargetFormatError("target must look like <os>-<arch>")
    return build_target(parts[0], parts[1])


def detect_current_target(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> PlatformTarget:
    return build_target(system or platform.system(), machine or platform.machine())

