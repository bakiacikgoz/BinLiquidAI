from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = REPO_ROOT / "contracts" / "operator_panel" / "schemas"
GENERATOR_PATH = REPO_ROOT / "scripts" / "generate_operator_contract_schemas.py"


def _load_schema_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "generate_operator_contract_schemas",
        GENERATOR_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCHEMAS = _load_schema_generator().SCHEMAS


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def test_operator_panel_schemas_are_generated_from_contract_models() -> None:
    mismatches: list[str] = []
    for name, model in SCHEMAS.items():
        path = SCHEMA_ROOT / f"{name}.schema.json"
        expected = _canonical_json(model.model_json_schema())
        actual = path.read_text(encoding="utf-8")
        if actual != expected:
            mismatches.append(str(path.relative_to(Path(__file__).resolve().parents[1])))

    assert not mismatches, (
        "Operator panel schema drift detected. Run "
        "`uv run python scripts/generate_operator_contract_schemas.py` and commit the result: "
        + ", ".join(mismatches)
    )
