from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from imperaos.artifacts import migrations
from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.migrations import (
    ArtifactMigration,
    connect_artifact_metadata,
    migrate_artifact_metadata,
)


def test_migration_dry_run_reports_capacity_without_creating_database(tmp_path: Path) -> None:
    database = tmp_path / "metadata" / "artifacts.sqlite3"

    report = migrate_artifact_metadata(database, dry_run=True)

    assert report.current_version == 0
    assert report.target_version == 3
    assert report.pending_versions == (1, 2, 3)
    assert report.applied_versions == ()
    assert report.database_size_bytes == 0
    assert report.free_space_bytes > 0
    assert not database.exists()
    assert not database.parent.exists()


def test_migrations_apply_forward_only_schema_and_runtime_pragmas(tmp_path: Path) -> None:
    database = tmp_path / "metadata" / "artifacts.sqlite3"

    report = migrate_artifact_metadata(database, busy_timeout_ms=2_500)

    assert report.applied_versions == (1, 2, 3)
    with connect_artifact_metadata(database, busy_timeout_ms=2_500) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        versions = connection.execute(
            "SELECT version, checksum FROM artifact_schema_migrations ORDER BY version"
        ).fetchall()

        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 2_500
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3

    assert {
        "artifacts",
        "artifact_revisions",
        "artifact_assets",
        "artifact_links",
        "artifact_operation_dedup",
        "artifact_exports",
        "form_submissions",
    } <= tables
    assert {
        "idx_artifacts_workspace_updated",
        "idx_artifacts_workspace_kind_status",
    } <= indexes
    assert [row[0] for row in versions] == [1, 2, 3]
    assert all(len(row[1]) == 64 for row in versions)


def test_migrations_are_idempotent_and_dry_run_does_not_touch_existing_db(
    tmp_path: Path,
) -> None:
    database = tmp_path / "artifacts.sqlite3"
    migrate_artifact_metadata(database)
    timestamp_before = database.stat().st_mtime_ns

    dry_run = migrate_artifact_metadata(database, dry_run=True)
    applied_again = migrate_artifact_metadata(database)

    assert dry_run.pending_versions == ()
    assert dry_run.applied_versions == ()
    assert applied_again.applied_versions == ()
    assert database.stat().st_mtime_ns == timestamp_before


def test_migrations_reject_destructive_downgrade_and_unbounded_timeout(
    tmp_path: Path,
) -> None:
    database = tmp_path / "artifacts.sqlite3"
    migrate_artifact_metadata(database)

    with pytest.raises(ArtifactDomainError) as caught:
        migrate_artifact_metadata(database, target_version=2)
    assert caught.value.code is ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT
    assert caught.value.details["classification"] == "destructive_downgrade_denied"

    with pytest.raises(ValueError, match="busy_timeout_ms"):
        connect_artifact_metadata(database, busy_timeout_ms=60_001)

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3


def test_failed_migration_rolls_back_version_and_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "artifacts.sqlite3"
    migrate_artifact_metadata(database)
    broken = ArtifactMigration(
        version=4,
        name="broken_test_migration",
        statements=("CREATE TABLE must_roll_back (id TEXT)", "NOT VALID SQL"),
    )
    monkeypatch.setattr(migrations, "MIGRATIONS", (*migrations.MIGRATIONS, broken))

    with pytest.raises(ArtifactDomainError) as caught:
        migrate_artifact_metadata(database)

    assert caught.value.code is ArtifactErrorCode.ARTIFACT_STORAGE_CORRUPT
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM artifact_schema_migrations WHERE version = 4"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE name = 'must_roll_back'"
            ).fetchone()[0]
            == 0
        )
