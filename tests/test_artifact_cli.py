from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from imperaos.artifacts.commands import CreateArtifactCommand
from imperaos.artifacts.models import (
    ArtifactDataClass,
    ArtifactKind,
    OperationContext,
    PrincipalType,
)
from imperaos.artifacts.service import ArtifactService
from imperaos.cli import app

runner = CliRunner()


def _seed(root: Path) -> None:
    service = ArtifactService(root)
    service.create(
        CreateArtifactCommand(
            artifact_id="artifact-1",
            kind=ArtifactKind.DOCUMENT,
            title="CLI document",
            data_class=ArtifactDataClass.INTERNAL,
            content={
                "kind": "document",
                "schemaVersion": 1,
                "language": "tr",
                "pageMode": "document",
                "blocks": [],
            },
            idempotency_key="create-1",
        ),
        OperationContext(
            workspace_id="workspace-1",
            principal_type=PrincipalType.USER,
            principal_id="user-1",
            roles=("artifact_admin",),
            request_id="seed-1",
        ),
    )


def test_artifact_cli_doctor_list_get_history_and_integrity(tmp_path: Path) -> None:
    root = tmp_path / "artifact-root"
    _seed(root)

    doctor = runner.invoke(app, ["artifact", "doctor", "--root", str(root)])
    listed = runner.invoke(
        app,
        ["artifact", "list", "--root", str(root), "--workspace", "workspace-1"],
    )
    loaded = runner.invoke(
        app,
        [
            "artifact",
            "get",
            "artifact-1",
            "--root",
            str(root),
            "--workspace",
            "workspace-1",
        ],
    )
    history = runner.invoke(
        app,
        [
            "artifact",
            "history",
            "artifact-1",
            "--root",
            str(root),
            "--workspace",
            "workspace-1",
        ],
    )
    integrity = runner.invoke(
        app,
        [
            "artifact",
            "integrity",
            "verify",
            "--root",
            str(root),
            "--workspace",
            "workspace-1",
        ],
    )

    assert doctor.exit_code == 0, doctor.output
    assert json.loads(doctor.output)["status"] == "ready"
    assert json.loads(doctor.output)["schemaVersion"] == 4
    assert json.loads(listed.output)["count"] == 1
    assert json.loads(loaded.output)["artifact"]["artifactId"] == "artifact-1"
    assert len(json.loads(history.output)["items"]) == 1
    assert json.loads(integrity.output) == {
        "artifactCount": 1,
        "revisionCount": 1,
        "status": "pass",
        "workspaceRef": "workspace-1",
    }


def test_artifact_cli_migration_plan_is_dry_and_workspace_rpc_is_registered(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifact-root"

    plan = runner.invoke(
        app,
        ["artifact", "migration", "plan", "--root", str(root)],
    )
    rpc_help = runner.invoke(app, ["workspace-rpc", "--help"])

    payload = json.loads(plan.output)
    assert plan.exit_code == 0, plan.output
    assert payload["targetVersion"] == 4
    assert payload["pendingVersions"] == [1, 2, 3, 4]
    assert not root.exists()
    assert rpc_help.exit_code == 0
    assert "--stdio-json" in rpc_help.output
