from __future__ import annotations

from pathlib import Path

from artifact_store_support import make_artifact_pair

from imperaos.artifacts.models import ArtifactMutationType
from imperaos.artifacts.store import ArtifactStore


def test_store_creates_gets_and_lists_immutable_revisions(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifact-root")
    artifact, revision = make_artifact_pair(b'{"version":1}')

    created = store.create_artifact(artifact, revision, b'{"version":1}')
    loaded = store.get_artifact("workspace-1", "artifact-1")
    stored_revision = store.get_revision("workspace-1", "artifact-1", "revision-1")

    assert created.created is True
    assert created.disposition == "created"
    assert loaded == artifact
    assert stored_revision.descriptor == revision
    assert stored_revision.content == b'{"version":1}'
    assert store.list_revisions("workspace-1", "artifact-1") == (revision,)


def test_store_suppresses_noop_and_restores_as_a_new_revision(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifact-root")
    artifact_v1, revision_v1 = make_artifact_pair(b'{"version":1}')
    store.create_artifact(artifact_v1, revision_v1, b'{"version":1}')

    artifact_v2, revision_v2 = make_artifact_pair(
        b'{"version":2}',
        revision_number=2,
        parent_revision_id="revision-1",
    )
    store.append_revision(
        artifact_v2,
        revision_v2,
        b'{"version":2}',
        expected_revision_number=1,
    )
    artifact_noop, revision_noop = make_artifact_pair(
        b'{"version":2}',
        revision_number=3,
        revision_id="revision-noop",
        parent_revision_id="revision-2",
    )

    noop = store.append_revision(
        artifact_noop,
        revision_noop,
        b'{"version":2}',
        expected_revision_number=2,
    )
    artifact_v3, revision_v3 = make_artifact_pair(
        b'{"version":1}',
        revision_number=3,
        parent_revision_id="revision-2",
        base_revision_id="revision-1",
        mutation_type=ArtifactMutationType.RESTORE,
    )
    restored = store.restore_revision(
        artifact_v3,
        revision_v3,
        source_revision_id="revision-1",
        expected_revision_number=2,
    )

    assert noop.created is False
    assert noop.disposition == "no_op"
    assert restored.created is True
    assert store.get_revision("workspace-1", "artifact-1", "revision-3").content == b'{"version":1}'
    assert [item.revision_number for item in store.list_revisions("workspace-1", "artifact-1")] == [
        3,
        2,
        1,
    ]
