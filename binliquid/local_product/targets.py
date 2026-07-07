from __future__ import annotations

from typing import Literal

from pydantic import Field

from binliquid.local_product.platforms import (
    EXPERIMENTAL_TARGETS,
    SUPPORTED_TARGETS,
    detect_current_target,
    parse_target,
)
from binliquid.memory.models import StrictModel

ClaimLevel = Literal[
    "not_claimed",
    "source_supported",
    "internal_desktop_validated",
    "public_release_blocked",
]
RunnerMode = Literal["github_hosted", "self_hosted", "manual_or_ci"]


class PlatformTargetDefinition(StrictModel):
    target_id: str = Field(alias="targetId")
    os: Literal["darwin", "windows", "linux"] | str
    arch: Literal["arm64", "x64"] | str
    claim_level: ClaimLevel = Field(alias="claimLevel")
    required_evidence: list[str] = Field(default_factory=list, alias="requiredEvidence")
    runner_mode: RunnerMode = Field(default="manual_or_ci", alias="runnerMode")
    experimental: bool = False


DEFAULT_REQUIRED_EVIDENCE = ["local_readiness"]


def default_target_registry(*, include_experimental: bool = True) -> list[PlatformTargetDefinition]:
    targets: list[PlatformTargetDefinition] = []
    for target_id in SUPPORTED_TARGETS:
        target = parse_target(target_id)
        targets.append(
            PlatformTargetDefinition(
                targetId=target.target_id,
                os=target.os,
                arch=target.arch,
                claimLevel="source_supported",
                requiredEvidence=list(DEFAULT_REQUIRED_EVIDENCE),
                runnerMode="manual_or_ci",
                experimental=False,
            )
        )
    if include_experimental:
        for target_id in EXPERIMENTAL_TARGETS:
            target = parse_target(target_id)
            targets.append(
                PlatformTargetDefinition(
                    targetId=target.target_id,
                    os=target.os,
                    arch=target.arch,
                    claimLevel="not_claimed",
                    requiredEvidence=list(DEFAULT_REQUIRED_EVIDENCE),
                    runnerMode="manual_or_ci",
                    experimental=True,
                )
            )
    return targets


def parse_platform_target(raw: str) -> PlatformTargetDefinition:
    value = raw.strip().lower()
    target = detect_current_target() if value == "current" else parse_target(value)
    for definition in default_target_registry(include_experimental=True):
        if definition.target_id == target.target_id:
            return definition
    return PlatformTargetDefinition(
        targetId=target.target_id,
        os=target.os,
        arch=target.arch,
        claimLevel="not_claimed",
        requiredEvidence=[],
        runnerMode="manual_or_ci",
        experimental=True,
    )


def resolve_current_platform_target() -> PlatformTargetDefinition:
    return parse_platform_target("current")
