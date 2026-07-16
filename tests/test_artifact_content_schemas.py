from __future__ import annotations

import pytest
from pydantic import ValidationError

from imperaos.artifacts.content import (
    ARTIFACT_CONTENT_MODEL_BY_KIND,
    SafeJsonPatch,
    validate_artifact_content,
)
from imperaos.artifacts.models import ArtifactKind

VALID_CONTENT: dict[ArtifactKind, dict[str, object]] = {
    ArtifactKind.DOCUMENT: {
        "kind": "document",
        "schemaVersion": 1,
        "language": "tr",
        "pageMode": "document",
        "blocks": [
            {"id": "block-1", "type": "paragraph", "content": [{"type": "text", "text": "Merhaba"}]}
        ],
    },
    ArtifactKind.FORM: {
        "kind": "form",
        "schemaVersion": 1,
        "schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "maxLength": 100}},
            "required": ["name"],
            "additionalProperties": False,
        },
        "uiSchema": {"name": {"ui:widget": "text"}},
        "behavior": {"submitMode": "explicit", "externalContinuation": "approval_required"},
        "sensitivePaths": ["/name"],
    },
    ArtifactKind.CODE: {
        "kind": "code",
        "schemaVersion": 1,
        "filename": "main.py",
        "language": "python",
        "text": "print('display only')\n",
        "lineEnding": "lf",
        "executionPolicy": "deny",
    },
    ArtifactKind.FLOW: {
        "kind": "flow",
        "schemaVersion": 1,
        "nodes": [
            {
                "id": "node-1",
                "type": "input",
                "position": {"x": 0, "y": 0},
                "data": {"label": "Start"},
            },
            {
                "id": "node-2",
                "type": "output",
                "position": {"x": 100, "y": 0},
                "data": {"label": "End"},
            },
        ],
        "edges": [{"id": "edge-1", "source": "node-1", "target": "node-2"}],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    },
    ArtifactKind.SPREADSHEET: {
        "kind": "spreadsheet",
        "schemaVersion": 1,
        "calculationMode": "disabled",
        "sheets": [
            {"id": "sheet-1", "name": "Sheet 1", "cells": {"A1": {"value": "Safe"}}, "columns": []}
        ],
    },
    ArtifactKind.CANVAS: {
        "kind": "canvas",
        "schemaVersion": 1,
        "snapshot": {"store": {"shape:1": {"typeName": "shape", "assetId": "asset-1"}}},
        "assetIds": ["asset-1"],
        "embeds": "deny",
        "remoteAssets": "deny",
    },
    ArtifactKind.SLIDES: {
        "kind": "slides",
        "schemaVersion": 1,
        "theme": {"name": "ImperaOS"},
        "slides": [
            {"id": "slide-1", "elements": [{"id": "element-1", "type": "text", "text": "Title"}]}
        ],
    },
}


@pytest.mark.parametrize("kind", list(ArtifactKind))
def test_each_v1_artifact_content_schema_accepts_its_minimal_contract(kind: ArtifactKind) -> None:
    content = validate_artifact_content(kind, VALID_CONTENT[kind])

    assert content.kind == kind.value
    assert content.schema_version == 1


def test_artifact_content_registry_is_complete_and_kind_discriminated() -> None:
    assert set(ARTIFACT_CONTENT_MODEL_BY_KIND) == set(ArtifactKind)

    mismatched = dict(VALID_CONTENT[ArtifactKind.CODE])
    mismatched["kind"] = "document"
    with pytest.raises(ValidationError):
        validate_artifact_content(ArtifactKind.CODE, mismatched)


def test_safe_json_patch_rejects_prototype_pollution_and_unsafe_operations() -> None:
    patch = SafeJsonPatch.model_validate(
        {"operations": [{"op": "replace", "path": "/blocks/0/content/0/text", "value": "Updated"}]}
    )
    assert patch.operations[0].op == "replace"

    with pytest.raises(ValidationError, match="unsafe JSON Pointer"):
        SafeJsonPatch.model_validate(
            {"operations": [{"op": "add", "path": "/metadata/__proto__/polluted", "value": True}]}
        )
    with pytest.raises(ValidationError):
        SafeJsonPatch.model_validate(
            {"operations": [{"op": "move", "path": "/safe", "from": "/other"}]}
        )


def test_form_schema_rejects_remote_refs_eval_pressure_and_network_widgets() -> None:
    remote_ref = dict(VALID_CONTENT[ArtifactKind.FORM])
    remote_ref["schema"] = {"$ref": "https://example.com/schema.json"}
    with pytest.raises(ValidationError, match="remote refs"):
        validate_artifact_content(ArtifactKind.FORM, remote_ref)

    unsafe_pattern = dict(VALID_CONTENT[ArtifactKind.FORM])
    unsafe_pattern["schema"] = {
        "type": "object",
        "properties": {"value": {"type": "string", "pattern": "(a+)+$"}},
    }
    with pytest.raises(ValidationError, match="unsafe pattern"):
        validate_artifact_content(ArtifactKind.FORM, unsafe_pattern)

    network_widget = dict(VALID_CONTENT[ArtifactKind.FORM])
    network_widget["uiSchema"] = {"name": {"ui:widget": "html", "src": "https://example.com"}}
    with pytest.raises(ValidationError, match="uiSchema"):
        validate_artifact_content(ArtifactKind.FORM, network_widget)


def test_editor_schemas_keep_execution_calculation_and_remote_assets_disabled() -> None:
    executable = dict(VALID_CONTENT[ArtifactKind.CODE])
    executable["executionPolicy"] = "allow"
    with pytest.raises(ValidationError):
        validate_artifact_content(ArtifactKind.CODE, executable)

    calculated = dict(VALID_CONTENT[ArtifactKind.SPREADSHEET])
    calculated["calculationMode"] = "automatic"
    with pytest.raises(ValidationError):
        validate_artifact_content(ArtifactKind.SPREADSHEET, calculated)

    remote_canvas = dict(VALID_CONTENT[ArtifactKind.CANVAS])
    remote_canvas["snapshot"] = {"asset": {"src": "https://example.com/image.png"}}
    with pytest.raises(ValidationError, match="remote URL"):
        validate_artifact_content(ArtifactKind.CANVAS, remote_canvas)


def test_flow_edges_and_slide_count_are_bounded() -> None:
    invalid_flow = dict(VALID_CONTENT[ArtifactKind.FLOW])
    invalid_flow["edges"] = [{"id": "edge-bad", "source": "node-1", "target": "missing"}]
    with pytest.raises(ValidationError, match="unknown target"):
        validate_artifact_content(ArtifactKind.FLOW, invalid_flow)

    too_many_slides = dict(VALID_CONTENT[ArtifactKind.SLIDES])
    too_many_slides["slides"] = [{"id": f"slide-{index}", "elements": []} for index in range(201)]
    with pytest.raises(ValidationError):
        validate_artifact_content(ArtifactKind.SLIDES, too_many_slides)
