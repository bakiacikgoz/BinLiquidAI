from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field

from binliquid.local_product.artifact_sources import (
    ArtifactDiscoveryRequest,
    HarvestTargetResult,
    PlatformEvidenceHarvestReport,
    RemoteArtifactSource,
    current_git_branch,
    current_git_head,
    normalize_report_path,
)
from binliquid.local_product.evidence_importer import (
    DEFAULT_EVIDENCE_STORE,
    EvidenceImportError,
    import_platform_evidence_bundle,
)
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence
from binliquid.local_product.evidence_verifier import verify_platform_evidence_bundle
from binliquid.local_product.github_actions import GitHubActionsArtifactAdapter
from binliquid.memory.models import StrictModel


class HarvestRequest(StrictModel):
    profile: str = "enterprise"
    branch: str = Field(default_factory=current_git_branch)
    head_sha: str = Field(default_factory=current_git_head, alias="headSha")
    repo: str = "bakiacikgoz/BinLiquidAI"
    workflow: str | None = "local-product-platform-evidence.yml"
    output_root: str = Field(
        default="artifacts/local-product/harvest",
        alias="outputRoot",
    )
    evidence_store: str = Field(
        default=str(DEFAULT_EVIDENCE_STORE),
        alias="evidenceStore",
    )
    manual_bundle: str | None = Field(default=None, alias="manualBundle")
    import_verified: bool = Field(default=True, alias="importVerified")


def default_github_source(request: HarvestRequest) -> RemoteArtifactSource:
    return RemoteArtifactSource(
        sourceId="github-actions",
        sourceType="github_actions",
        repo=request.repo,
        workflow=request.workflow,
        branch=request.branch,
        headSha=request.head_sha,
        artifactPattern="local-product-evidence-*",
        authMode="auto",
    )


def harvest_platform_evidence(
    *,
    request: HarvestRequest,
    source: RemoteArtifactSource | None = None,
    adapter: GitHubActionsArtifactAdapter | None = None,
) -> PlatformEvidenceHarvestReport:
    output_root = Path(request.output_root)
    store_root = Path(request.evidence_store)
    output_root.mkdir(parents=True, exist_ok=True)
    source = source or default_github_source(request)
    adapter = adapter or GitHubActionsArtifactAdapter()
    target_results: list[HarvestTargetResult] = []
    warnings: list[str] = []
    blockers: list[str] = []
    downloaded_count = 0
    imported_count = 0

    discovery = adapter.discover(
        ArtifactDiscoveryRequest(
            source=source,
            branch=request.branch,
            headSha=request.head_sha,
            workflow=request.workflow,
        )
    )
    warnings.extend(discovery.warnings)
    if discovery.status in {"blocked", "fail"}:
        blockers.extend(discovery.reason_codes)

    bundles: list[Path] = []
    if request.manual_bundle:
        bundles.append(Path(request.manual_bundle))
    elif discovery.status == "pass":
        for artifact in discovery.artifacts:
            try:
                downloaded = adapter.download(artifact, output_root / "downloads")
                downloaded_count += 1
                bundles.append(Path(downloaded.downloaded_path))
                target_results.append(
                    HarvestTargetResult(
                        target=artifact.target or "unknown",
                        status="downloaded",
                        sourceId=artifact.source_id,
                        artifactId=artifact.artifact_id,
                        bundleSha256=downloaded.sha256,
                    )
                )
            except ValueError as exc:
                target_results.append(
                    HarvestTargetResult(
                        target=artifact.target or "unknown",
                        status="blocked",
                        sourceId=artifact.source_id,
                        artifactId=artifact.artifact_id,
                        reasonCodes=[str(exc)],
                    )
                )

    for bundle in bundles:
        verification = verify_platform_evidence_bundle(
            bundle_path=bundle,
            expected_commit=request.head_sha,
        )
        target = verification.target_id or "unknown"
        if verification.status != "pass":
            target_results.append(
                HarvestTargetResult(
                    target=target,
                    status="blocked",
                    bundleSha256=None,
                    reasonCodes=verification.reason_codes,
                )
            )
            continue
        if not request.import_verified:
            continue
        try:
            imported = import_platform_evidence_bundle(
                bundle_path=bundle,
                store_root=store_root,
                verification=verification,
            )
            imported_count += 1 if imported.status == "imported" else 0
            target_results.append(
                HarvestTargetResult(
                    target=imported.target_id,
                    status="evidenced",
                    bundleSha256=imported.bundle_sha256,
                    evidenceId=imported.evidence_id,
                    reasonCodes=[],
                )
            )
        except EvidenceImportError:
            target_results.append(
                HarvestTargetResult(
                    target=target,
                    status="blocked",
                    reasonCodes=["PLATFORM_EVIDENCE_IMPORT_REJECTED"],
                )
            )

    reconciliation = reconcile_platform_evidence(
        store_root=store_root,
        current_commit=request.head_sha,
    )
    for target in reconciliation.not_evidenced_targets:
        if all(result.target != target for result in target_results):
            target_results.append(
                HarvestTargetResult(
                    target=target,
                    status="not_evidenced",
                    reasonCodes=["TARGET_NOT_EVIDENCED"],
                )
            )

    if blockers:
        status = "blocked"
    elif discovery.status == "conditional" and not request.manual_bundle:
        status = "conditional"
    else:
        status = "pass"

    report = PlatformEvidenceHarvestReport(
        status=status,
        headSha=request.head_sha,
        branch=request.branch,
        sources=[source],
        artifactsDiscovered=len(discovery.artifacts),
        artifactsDownloaded=downloaded_count,
        artifactsImported=imported_count,
        targetResults=sorted(target_results, key=lambda item: (item.target, item.status)),
        blockers=sorted(set(blockers)),
        warnings=sorted(set([*warnings, *discovery.reason_codes])),
        reconciliation=reconciliation.model_dump(mode="json", by_alias=True),
        outputRoot=normalize_report_path(output_root),
    )
    (output_root / "platform_evidence_harvest_report.json").write_text(
        json.dumps(report.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return report

