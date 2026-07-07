from __future__ import annotations

from pathlib import Path

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.evidence_importer import import_platform_evidence_bundle
from binliquid.local_product.evidence_verifier import load_manifest_from_bundle
from binliquid.local_product.source_install_claim import (
    SourceInstallClaimPolicy,
    build_source_install_rc_claim,
)


def _store_with_windows(tmp_path: Path) -> tuple[Path, str]:
    collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    export_platform_evidence_bundle(
        manifest_path=tmp_path / "evidence" / "platform_evidence_manifest.json",
        bundle_path=tmp_path / "bundle.zip",
    )
    import_platform_evidence_bundle(
        bundle_path=tmp_path / "bundle.zip",
        store_root=tmp_path / "store",
    )
    return tmp_path / "store", load_manifest_from_bundle(tmp_path / "bundle.zip").git_commit


def test_source_claim_only_claims_evidenced_targets(tmp_path: Path) -> None:
    store, head = _store_with_windows(tmp_path)

    claim = build_source_install_rc_claim(
        policy=SourceInstallClaimPolicy(expectedHeadSha=head),
        evidence_root=store,
    )

    assert claim.status == "pass"
    assert claim.claimed_targets == ["windows-x64"]
    assert "linux-x64" in claim.not_evidenced_targets


def test_source_claim_overclaim_blocks(tmp_path: Path) -> None:
    store, head = _store_with_windows(tmp_path)

    claim = build_source_install_rc_claim(
        policy=SourceInstallClaimPolicy(
            expectedHeadSha=head,
            requestedTargets=["linux-x64"],
        ),
        evidence_root=store,
    )

    assert claim.status == "blocked"
    assert claim.no_ship_blockers == ["SOURCE_INSTALL_TARGET_WITHOUT_EVIDENCE"]


def test_source_claim_stale_evidence_blocks(tmp_path: Path) -> None:
    store, _head = _store_with_windows(tmp_path)

    claim = build_source_install_rc_claim(
        policy=SourceInstallClaimPolicy(expectedHeadSha="b" * 40),
        evidence_root=store,
    )

    assert claim.status == "blocked"
    assert "SOURCE_INSTALL_TARGET_STALE" in claim.no_ship_blockers

