from __future__ import annotations

import json
from pathlib import Path

import pytest

from imperaos.artifacts.commands import (
    ArchiveArtifactCommand,
    ArtifactHistoryQuery,
    BeginArtifactExportCommand,
    CreateArtifactCommand,
    GetArtifactQuery,
)
from imperaos.artifacts.errors import ArtifactDomainError, ArtifactErrorCode
from imperaos.artifacts.feature_flags import (
    ARTIFACT_FEATURE_FLAG_NAMES,
    resolve_artifact_feature_flags,
)
from imperaos.artifacts.models import (
    ArtifactDataClass,
    ArtifactKind,
    OperationContext,
    PrincipalType,
)
from imperaos.artifacts.runtime import resolve_runtime_artifact_feature_flags
from imperaos.artifacts.service import ArtifactService


def test_feature_flag_contract_has_the_exact_phase_24_names() -> None:
    root = Path(__file__).resolve().parents[1]
    contract = json.loads(
        (root / "contracts/artifact_workspace/feature_flags.json").read_text(
            encoding="utf-8"
        )
    )
    assert tuple(contract["flags"]) == ARTIFACT_FEATURE_FLAG_NAMES
    assert all(value is False for value in contract["defaults"].values())


def test_global_off_and_license_capabilities_are_authoritative() -> None:
    requested = {name: True for name in ARTIFACT_FEATURE_FLAG_NAMES}
    requested["artifact_workspace.enabled"] = False
    global_off = resolve_artifact_feature_flags(
        requested,
        license_capabilities={"spreadsheet": True, "canvas": True},
    )
    assert all(value is False for value in global_off.values())

    requested["artifact_workspace.enabled"] = True
    resolved = resolve_artifact_feature_flags(
        requested,
        license_capabilities={"spreadsheet": False, "canvas": False},
    )
    assert resolved["artifact_workspace.document.enabled"] is True
    assert resolved["artifact_workspace.spreadsheet.enabled"] is False
    assert resolved["artifact_workspace.canvas.enabled"] is False


def test_runtime_flags_default_off_and_service_revalidates_authority(
    tmp_path: Path,
) -> None:
    disabled = resolve_runtime_artifact_feature_flags(env={})
    assert all(value is False for value in disabled.values())

    service = ArtifactService(tmp_path / "artifacts", feature_flags=disabled)
    command = CreateArtifactCommand(
        artifact_id="artifact-disabled",
        kind=ArtifactKind.DOCUMENT,
        title="Disabled",
        data_class=ArtifactDataClass.INTERNAL,
        content={
            "kind": "document",
            "schemaVersion": 1,
            "language": "tr",
            "pageMode": "document",
            "blocks": [],
        },
        idempotency_key="disabled-create",
    )
    context = OperationContext(
        workspace_id="workspace-1",
        principal_type=PrincipalType.USER,
        principal_id="user-1",
        roles=("artifact_editor",),
        request_id="request-disabled",
    )
    with pytest.raises(ArtifactDomainError) as caught:
        service.create(command, context)
    assert caught.value.code is ArtifactErrorCode.ARTIFACT_POLICY_UNAVAILABLE
    assert caught.value.details["reasonCode"] == "ARTIFACT_FEATURE_DISABLED"

    enabled = resolve_runtime_artifact_feature_flags(
        env={
            "IMPERAOS_ARTIFACT_WORKSPACE_ENABLED": "true",
            "IMPERAOS_ARTIFACT_DOCUMENT_EDITOR_ENABLED": "1",
        }
    )
    assert enabled["artifact_workspace.enabled"] is True
    assert enabled["artifact_workspace.document.enabled"] is True
    assert enabled["artifact_workspace.form.enabled"] is False


def test_forced_off_editor_flag_preserves_read_archive_and_safe_export_fallback(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifacts"
    context = OperationContext(
        workspace_id="workspace-1",
        principal_type=PrincipalType.USER,
        principal_id="user-1",
        roles=("artifact_admin",),
        request_id="request-fallback",
    )
    created = ArtifactService(root).create(
        CreateArtifactCommand(
            artifact_id="spreadsheet-fallback",
            kind=ArtifactKind.SPREADSHEET,
            title="Fallback sheet",
            data_class=ArtifactDataClass.INTERNAL,
            content={
                "kind": "spreadsheet",
                "schemaVersion": 1,
                "calculationMode": "disabled",
                "sheets": [
                    {"id": "sheet-1", "name": "Sheet 1", "cells": {}, "columns": []}
                ],
            },
            idempotency_key="create-fallback",
        ),
        context,
    )
    flags = {name: True for name in ARTIFACT_FEATURE_FLAG_NAMES}
    flags["artifact_workspace.spreadsheet.enabled"] = False
    fallback = ArtifactService(root, feature_flags=flags)

    assert fallback.get(GetArtifactQuery(artifact_id="spreadsheet-fallback"), context).artifact
    assert fallback.history(
        ArtifactHistoryQuery(artifact_id="spreadsheet-fallback"), context
    ).items
    export = fallback.begin_export(
        BeginArtifactExportCommand(
            artifact_id="spreadsheet-fallback",
            revision_id=created.revision.revision_id,
            format="xlsx",
            idempotency_key="export-fallback",
        ),
        context,
    )
    assert export.disposition == "created"
    archived = fallback.archive(
        ArchiveArtifactCommand(
            artifact_id="spreadsheet-fallback",
            expected_revision_number=1,
        ),
        context,
    )
    assert archived.artifact.status.value == "archived"
