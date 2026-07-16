from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from imperaos.artifacts.commands import (
    ArtifactHistoryQuery,
    GetArtifactQuery,
    ListArtifactsQuery,
)
from imperaos.artifacts.migrations import ArtifactMigrationReport, migrate_artifact_metadata
from imperaos.artifacts.models import OperationContext, PrincipalType
from imperaos.artifacts.rpc_protocol import (
    ARTIFACT_RPC_CONTRACT_VERSION,
    ARTIFACT_RPC_MAX_FRAME_BYTES,
)
from imperaos.artifacts.rpc_server import ArtifactRpcServer
from imperaos.artifacts.service import ArtifactService
from imperaos.runtime.paths import state_path

DEFAULT_ARTIFACT_ROOT = Path(state_path("artifacts"))
ARTIFACT_ROOT_OPTION = typer.Option(
    DEFAULT_ARTIFACT_ROOT,
    "--root",
    help="Artifact data root",
)

artifact_app = typer.Typer(help="Artifact workspace diagnostics")
artifact_integrity_app = typer.Typer(help="Artifact integrity diagnostics")
artifact_migration_app = typer.Typer(help="Artifact metadata migration commands")
artifact_app.add_typer(artifact_integrity_app, name="integrity")
artifact_app.add_typer(artifact_migration_app, name="migration")


def register_artifact_cli(root_app: typer.Typer) -> None:
    root_app.add_typer(artifact_app, name="artifact")
    root_app.command("workspace-rpc")(workspace_rpc)


@artifact_app.command("doctor")
def artifact_doctor(
    root: Path = ARTIFACT_ROOT_OPTION,
) -> None:
    service = ArtifactService(root)
    report = migrate_artifact_metadata(service.store.database_path, dry_run=True)
    _emit(
        {
            "status": "ready",
            "schemaVersion": report.current_version,
            "protocolVersion": ARTIFACT_RPC_CONTRACT_VERSION,
            "maxFrameBytes": ARTIFACT_RPC_MAX_FRAME_BYTES,
            "networkListener": False,
            "evidenceChainTable": True,
        }
    )


@artifact_app.command("list")
def artifact_list(
    workspace: str = typer.Option(..., "--workspace", help="Workspace identity"),
    root: Path = ARTIFACT_ROOT_OPTION,
    limit: int = typer.Option(50, "--limit", min=1, max=200),
) -> None:
    result = ArtifactService(root).list(
        ListArtifactsQuery(limit=limit),
        _diagnostic_context(workspace, "artifact-cli-list"),
    )
    _emit(
        {
            "count": len(result.items),
            "items": [item.model_dump(mode="json", by_alias=True) for item in result.items],
            "nextCursor": result.next_cursor,
        }
    )


@artifact_app.command("get")
def artifact_get(
    artifact_id: str = typer.Argument(..., help="Artifact identity"),
    workspace: str = typer.Option(..., "--workspace", help="Workspace identity"),
    root: Path = ARTIFACT_ROOT_OPTION,
    revision_id: str | None = typer.Option(None, "--revision", help="Optional revision identity"),
) -> None:
    result = ArtifactService(root).get(
        GetArtifactQuery(artifact_id=artifact_id, revision_id=revision_id),
        _diagnostic_context(workspace, "artifact-cli-get"),
    )
    _emit(
        {
            "artifact": result.artifact.model_dump(mode="json", by_alias=True),
            "revision": result.revision.model_dump(mode="json", by_alias=True),
            "content": result.content.model_dump(mode="json", by_alias=True),
        }
    )


@artifact_app.command("history")
def artifact_history(
    artifact_id: str = typer.Argument(..., help="Artifact identity"),
    workspace: str = typer.Option(..., "--workspace", help="Workspace identity"),
    root: Path = ARTIFACT_ROOT_OPTION,
    limit: int = typer.Option(100, "--limit", min=1, max=500),
) -> None:
    result = ArtifactService(root).history(
        ArtifactHistoryQuery(artifact_id=artifact_id, limit=limit),
        _diagnostic_context(workspace, "artifact-cli-history"),
    )
    _emit(
        {
            "items": [item.model_dump(mode="json", by_alias=True) for item in result.items],
            "nextCursor": result.next_cursor,
        }
    )


@artifact_integrity_app.command("verify")
def artifact_integrity_verify(
    workspace: str = typer.Option(..., "--workspace", help="Workspace identity"),
    root: Path = ARTIFACT_ROOT_OPTION,
) -> None:
    service = ArtifactService(root)
    artifact_count = 0
    revision_count = 0
    offset = 0
    while True:
        artifacts = service.store.list_artifacts(workspace, limit=200, offset=offset)
        for artifact in artifacts:
            artifact_count += 1
            revisions = service.store.list_revisions(workspace, artifact.artifact_id)
            for revision in revisions:
                service.store.get_revision(workspace, artifact.artifact_id, revision.revision_id)
                revision_count += 1
        if len(artifacts) < 200:
            break
        offset += len(artifacts)
    _emit(
        {
            "status": "pass",
            "workspaceRef": workspace,
            "artifactCount": artifact_count,
            "revisionCount": revision_count,
        }
    )


@artifact_migration_app.command("plan")
def artifact_migration_plan(
    root: Path = ARTIFACT_ROOT_OPTION,
) -> None:
    report = migrate_artifact_metadata(
        root / "metadata" / "artifacts.sqlite3",
        dry_run=True,
    )
    _emit_migration(report)


@artifact_migration_app.command("apply")
def artifact_migration_apply(
    root: Path = ARTIFACT_ROOT_OPTION,
    dry_run: bool = typer.Option(False, "--dry-run", help="Report without writing"),
) -> None:
    report = migrate_artifact_metadata(
        root / "metadata" / "artifacts.sqlite3",
        dry_run=dry_run,
    )
    _emit_migration(report)


def workspace_rpc(
    stdio_json: bool = typer.Option(
        False,
        "--stdio-json",
        help="Serve length-prefixed JSON frames over stdin/stdout",
    ),
    root: Path = ARTIFACT_ROOT_OPTION,
) -> None:
    if not stdio_json:
        raise typer.BadParameter("--stdio-json is required")
    server = ArtifactRpcServer(ArtifactService(root))
    exit_code = server.serve(sys.stdin.buffer, sys.stdout.buffer, sys.stderr.buffer)
    raise typer.Exit(exit_code)


def _diagnostic_context(workspace: str, request_id: str) -> OperationContext:
    return OperationContext(
        workspace_id=workspace,
        principal_type=PrincipalType.SYSTEM,
        principal_id="artifact-cli",
        roles=("artifact_admin",),
        request_id=request_id,
    )


def _emit_migration(report: ArtifactMigrationReport) -> None:
    _emit(
        {
            "currentVersion": report.current_version,
            "targetVersion": report.target_version,
            "pendingVersions": list(report.pending_versions),
            "appliedVersions": list(report.applied_versions),
            "databaseExists": report.database_exists,
            "databaseSizeBytes": report.database_size_bytes,
            "freeSpaceBytes": report.free_space_bytes,
            "storageFileCount": report.storage_file_count,
            "tableRowCounts": report.table_row_counts,
        }
    )


def _emit(payload: dict[str, object]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
