from __future__ import annotations

import pytest

from binliquid.local_product.artifact_sources import (
    ArtifactDiscoveryRequest,
    RemoteArtifactSource,
)
from binliquid.local_product.github_actions import (
    GitHubActionsArtifactAdapter,
    _parse_github_artifacts,
)


def test_remote_artifact_source_validates_safe_pattern() -> None:
    with pytest.raises(ValueError, match="INVALID_ARTIFACT_PATTERN"):
        RemoteArtifactSource(
            sourceId="bad",
            sourceType="github_actions",
            repo="bakiacikgoz/BinLiquidAI",
            artifactPattern="../secret-*",
        )


def test_github_adapter_auth_missing_returns_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("binliquid.local_product.github_actions.shutil.which", lambda _: None)
    source = RemoteArtifactSource(
        sourceId="github-actions",
        sourceType="github_actions",
        repo="bakiacikgoz/BinLiquidAI",
        artifactPattern="local-product-evidence-*",
    )

    report = GitHubActionsArtifactAdapter().discover(
        ArtifactDiscoveryRequest(
            source=source,
            branch="codex/test",
            headSha="a" * 40,
            workflow="local-product-platform-evidence.yml",
        )
    )

    assert report.status == "conditional"
    assert "blocked_external_auth" in report.reason_codes


def test_github_adapter_discovers_matching_artifacts_from_fixture() -> None:
    source = RemoteArtifactSource(
        sourceId="github-actions",
        sourceType="github_actions",
        repo="bakiacikgoz/BinLiquidAI",
        artifactPattern="local-product-evidence-*",
    )
    payload = {
        "artifacts": [
            {
                "id": 1,
                "name": "local-product-evidence-linux-x64-aaaaaaaa",
                "expired": False,
                "size_in_bytes": 123,
                "archive_download_url": "https://example.invalid/download?token=secret",
            },
            {"id": 2, "name": "other", "expired": False},
        ]
    }

    artifacts = _parse_github_artifacts(source=source, payload=payload, head_sha="a" * 40)

    assert len(artifacts) == 1
    assert artifacts[0].target == "linux-x64"
    assert artifacts[0].archive_download_url_redacted == "https://example.invalid/download"

