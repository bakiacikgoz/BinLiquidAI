from __future__ import annotations

from pathlib import Path

import pytest
from artifact_store_support import make_artifact_pair

from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.models import ArtifactStatus
from imperaos.artifacts.store import ArtifactStore


def test_hash_tamper_quarantines_revision_and_marks_artifact_corrupt(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifact-root")
    artifact, revision = make_artifact_pair(b"trusted")
    store.create_artifact(artifact, revision, b"trusted")
    path = store.filesystem.resolve_relative(revision.content_relpath)
    path.write_bytes(b"tampered")

    with pytest.raises(ArtifactDomainError) as caught:
        store.get_revision("workspace-1", "artifact-1", "revision-1")

    assert caught.value.code is ArtifactErrorCode.ARTIFACT_HASH_MISMATCH
    assert store.get_artifact("workspace-1", "artifact-1").status is ArtifactStatus.CORRUPT
    assert not path.exists()
    assert any(item.is_file() for item in store.filesystem.quarantine_root.rglob("*"))


def test_crash_after_content_write_is_reconciled_to_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = ArtifactStore(tmp_path / "artifact-root")
    artifact, revision = make_artifact_pair(b"orphan")

    def simulate_crash(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated process crash")

    monkeypatch.setattr(store, "_commit_create", simulate_crash)
    with pytest.raises(RuntimeError, match="simulated process crash"):
        store.create_artifact(artifact, revision, b"orphan")

    recovered = ArtifactStore(tmp_path / "artifact-root")
    report = recovered.reconcile_storage()

    assert report.pending_journals == 1
    assert report.quarantined_files == 1
    assert not recovered.filesystem.resolve_relative(revision.content_relpath).exists()
    assert any(item.is_file() for item in recovered.filesystem.quarantine_root.rglob("*"))
