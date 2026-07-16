from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "contracts/artifacts"
GENERATOR_PATH = REPO_ROOT / "scripts/generate_artifact_contract_schemas.py"


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_artifact_contract_schemas", GENERATOR_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def test_artifact_contract_schemas_are_generated_without_drift() -> None:
    generator = _load_generator()
    mismatches: list[str] = []

    for name, model in generator.SCHEMAS.items():
        path = SCHEMA_ROOT / f"{name}.schema.json"
        expected = _canonical_json(generator.schema_for(name, model))
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            mismatches.append(name)

    assert not mismatches, (
        "Artifact contract schema drift detected. Run "
        "`uv run python scripts/generate_artifact_contract_schemas.py`: " + ", ".join(mismatches)
    )


def test_artifact_contract_manifest_covers_seven_content_kinds_and_hashes() -> None:
    manifest = json.loads((SCHEMA_ROOT / "manifest.json").read_text(encoding="utf-8"))
    entries = {entry["name"]: entry for entry in manifest["schemas"]}
    content_names = {
        "document.v1",
        "form.v1",
        "code.v1",
        "flow.v1",
        "spreadsheet.v1",
        "canvas.v1",
        "slides.v1",
    }
    command_names = {
        "artifact-create-command.v1",
        "artifact-get-query.v1",
        "artifact-list-query.v1",
        "artifact-mutation-command.v1",
        "artifact-mutation-proposal-command.v1",
        "artifact-apply-proposal-command.v1",
        "artifact-history-query.v1",
        "artifact-restore-command.v1",
        "artifact-archive-command.v1",
        "artifact-duplicate-command.v1",
        "artifact-evidence-event.v1",
    }

    assert manifest["schemaVersion"] == "artifact-workspace.contract-manifest/v1"
    assert content_names <= set(entries)
    assert command_names <= set(entries)
    for name, entry in entries.items():
        payload = (SCHEMA_ROOT / entry["file"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"], name


def test_safe_patch_and_form_contracts_publish_fail_closed_metadata() -> None:
    patch_schema = json.loads(
        (SCHEMA_ROOT / "safe-json-patch.v1.schema.json").read_text(encoding="utf-8")
    )
    form_schema = json.loads((SCHEMA_ROOT / "form.v1.schema.json").read_text(encoding="utf-8"))
    patch_text = json.dumps(patch_schema, sort_keys=True)
    form_text = json.dumps(form_schema, sort_keys=True)

    assert '"move"' not in patch_text
    assert '"copy"' not in patch_text
    assert "unsafe-eval" in form_text
    assert "remote $ref" in form_text
