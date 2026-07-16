from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from imperaos.artifacts.content import (  # noqa: E402
    CanvasContentV1,
    CodeContentV1,
    DocumentContentV1,
    FlowContentV1,
    FormContentV1,
    SafeJsonPatch,
    SlidesContentV1,
    SpreadsheetContentV1,
)
from imperaos.artifacts.models import (  # noqa: E402
    ArtifactDescriptor,
    ArtifactRevisionDescriptor,
    OperationContext,
)

SCHEMAS = {
    "document.v1": DocumentContentV1,
    "form.v1": FormContentV1,
    "code.v1": CodeContentV1,
    "flow.v1": FlowContentV1,
    "spreadsheet.v1": SpreadsheetContentV1,
    "canvas.v1": CanvasContentV1,
    "slides.v1": SlidesContentV1,
    "artifact-descriptor.v1": ArtifactDescriptor,
    "artifact-revision.v1": ArtifactRevisionDescriptor,
    "operation-context.v1": OperationContext,
    "safe-json-patch.v1": SafeJsonPatch,
}
CONTENT_SCHEMA_NAMES = {
    "document.v1",
    "form.v1",
    "code.v1",
    "flow.v1",
    "spreadsheet.v1",
    "canvas.v1",
    "slides.v1",
}


def schema_for(name: str, model: type[Any]) -> dict[str, Any]:
    schema = model.model_json_schema(by_alias=True)
    schema["$id"] = f"https://schemas.imperaos.local/artifacts/{name}.schema.json"
    schema["x-imperaos-contract"] = name
    if name == "form.v1":
        schema["x-imperaos-security"] = {
            "validator": "CSP-safe ValidatorType; global unsafe-eval is forbidden",
            "refs": "local definitions only; remote $ref is forbidden",
            "authority": "backend revalidation is mandatory",
        }
    if name == "safe-json-patch.v1":
        schema["x-imperaos-security"] = {
            "operations": "add/remove/replace/test only",
            "paths": "prototype pollution segments are forbidden",
        }
    return schema


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def main() -> None:
    root = REPO_ROOT / "contracts" / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict[str, str]] = []
    for name, model in SCHEMAS.items():
        filename = f"{name}.schema.json"
        payload = _canonical_json(schema_for(name, model))
        payload_bytes = payload.encode("utf-8")
        (root / filename).write_bytes(payload_bytes)
        manifest_entries.append(
            {
                "name": name,
                "file": filename,
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
                "category": "content" if name in CONTENT_SCHEMA_NAMES else "contract",
            }
        )
    manifest = {
        "schemaVersion": "artifact-workspace.contract-manifest/v1",
        "generatedFrom": "imperaos.artifacts",
        "schemas": manifest_entries,
    }
    (root / "manifest.json").write_bytes(_canonical_json(manifest).encode("utf-8"))


if __name__ == "__main__":
    main()
