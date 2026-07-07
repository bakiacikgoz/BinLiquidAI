from __future__ import annotations

from typing import Literal

from pydantic import Field

from binliquid.local_product.artifact_sources import current_git_head, utc_now
from binliquid.local_product.evidence_importer import DEFAULT_EVIDENCE_STORE
from binliquid.local_product.evidence_models import PlatformEvidenceReconciliation
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence
from binliquid.memory.models import StrictModel


class TargetClosureAction(StrictModel):
    schema_version: Literal["target_closure_action/v1"] = Field(
        default="target_closure_action/v1",
        alias="schemaVersion",
    )
    target: str
    status: Literal["not_evidenced", "stale", "blocked"]
    recommended_path: Literal["hosted_ci", "self_hosted", "manual_local"] = Field(
        alias="recommendedPath"
    )
    commands: list[str]
    runbook: str
    blocking_for_current_claim: bool = Field(alias="blockingForCurrentClaim")
    reason_codes: list[str] = Field(default_factory=list, alias="reasonCodes")
    generated_at_utc: str = Field(default_factory=utc_now, alias="generatedAtUtc")


RUNBOOKS = {
    "darwin-arm64": "docs/MACOS_LOCAL_EVIDENCE_RUNBOOK.md",
    "darwin-x64": "docs/MACOS_LOCAL_EVIDENCE_RUNBOOK.md",
    "linux-x64": "docs/LINUX_CI_EVIDENCE_RUNBOOK.md",
    "windows-x64": "docs/REMOTE_PLATFORM_EVIDENCE_HARVEST_RUNBOOK.md",
}

EVIDENCE_MANIFEST_PATH = "artifacts/local-product/evidence/current/platform_evidence_manifest.json"


def _commands_for_target(target: str, head_sha: str) -> tuple[str, list[str]]:
    if target == "linux-x64":
        return (
            "hosted_ci",
            [
                "gh workflow run local-product-platform-evidence.yml "
                f"--ref {head_sha}",
                "uv run binliquid local-product ci harvest "
                f"--head-sha {head_sha} --json",
            ],
        )
    if target == "darwin-arm64":
        return (
            "manual_local",
            [
                "uv sync --python 3.11 --extra dev",
                "uv run binliquid local-product evidence collect "
                "--target current --profile enterprise --json",
                "uv run binliquid local-product evidence export "
                f"--manifest {EVIDENCE_MANIFEST_PATH} "
                "--bundle artifacts/local-product/evidence-bundles/darwin-arm64.zip --json",
            ],
        )
    if target == "darwin-x64":
        return (
            "self_hosted",
            [
                "uv run binliquid local-product evidence collect "
                "--target darwin-x64 --profile enterprise --json",
                "uv run binliquid local-product evidence export "
                f"--manifest {EVIDENCE_MANIFEST_PATH} "
                "--bundle artifacts/local-product/evidence-bundles/darwin-x64.zip --json",
            ],
        )
    return (
        "manual_local",
        [
            f"uv run binliquid local-product evidence collect --target {target} "
            "--profile enterprise --json",
            "uv run binliquid local-product source-install claim --profile enterprise --json",
        ],
    )


def build_target_closure_actions(
    *,
    reconciliation: PlatformEvidenceReconciliation | None = None,
    evidence_root=DEFAULT_EVIDENCE_STORE,
    head_sha: str | None = None,
) -> list[TargetClosureAction]:
    head_sha = head_sha or current_git_head()
    reconciliation = reconciliation or reconcile_platform_evidence(
        store_root=evidence_root,
        current_commit=head_sha,
    )
    actions: list[TargetClosureAction] = []
    for target_id, target in sorted(reconciliation.targets.items()):
        if target.status not in {"not_evidenced", "stale", "blocked"}:
            continue
        path, commands = _commands_for_target(target_id, head_sha)
        actions.append(
            TargetClosureAction(
                target=target_id,
                status=target.status,
                recommendedPath=path,
                commands=commands,
                runbook=RUNBOOKS.get(target_id, "docs/REMOTE_PLATFORM_EVIDENCE_HARVEST_RUNBOOK.md"),
                blockingForCurrentClaim=target_id in reconciliation.claimed_targets,
                reasonCodes=target.reason_codes,
            )
        )
    return actions
