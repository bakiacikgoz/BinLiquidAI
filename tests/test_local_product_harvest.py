from __future__ import annotations

from pathlib import Path

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.harvest import HarvestRequest, harvest_platform_evidence


def _bundle(tmp_path: Path) -> Path:
    collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    export_platform_evidence_bundle(
        manifest_path=tmp_path / "evidence" / "platform_evidence_manifest.json",
        bundle_path=tmp_path / "bundle.zip",
    )
    return tmp_path / "bundle.zip"


def test_harvest_imports_manual_bundle_idempotently(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    request = HarvestRequest(
        profile="enterprise",
        headSha="a" * 40,
        outputRoot=str(tmp_path / "harvest"),
        evidenceStore=str(tmp_path / "store"),
        manualBundle=str(bundle),
    )
    # Use the bundle commit as expected head to avoid relying on a hard-coded SHA.
    from binliquid.local_product.evidence_verifier import load_manifest_from_bundle

    request = request.model_copy(update={"head_sha": load_manifest_from_bundle(bundle).git_commit})

    first = harvest_platform_evidence(request=request)
    second = harvest_platform_evidence(request=request)

    assert first.status == "pass"
    assert second.status == "pass"
    assert "windows-x64" in second.reconciliation["evidencedTargets"]

def test_harvest_auth_missing_is_conditional(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("binliquid.local_product.github_actions.shutil.which", lambda _: None)

    report = harvest_platform_evidence(
        request=HarvestRequest(
            profile="enterprise",
            headSha="a" * 40,
            outputRoot=str(tmp_path / "harvest"),
            evidenceStore=str(tmp_path / "store"),
        )
    )

    assert report.status == "conditional"
    assert "blocked_external_auth" in report.warnings

