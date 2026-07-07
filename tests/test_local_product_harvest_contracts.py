from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def _schema(name: str) -> dict[str, object]:
    return json.loads((Path("contracts/local_product") / name).read_text(encoding="utf-8"))


def test_local_product_harvest_contract_schemas_are_generated() -> None:
    subprocess.run(
        [sys.executable, "scripts/generate_local_product_harvest_contract_schemas.py"],
        check=True,
    )

    for schema_name in [
        "remote_artifact_source.schema.json",
        "platform_evidence_harvest.schema.json",
        "source_install_rc_claim.schema.json",
        "target_closure_action.schema.json",
    ]:
        assert (Path("contracts/local_product") / schema_name).exists()


def test_local_product_harvest_contract_fixtures_validate() -> None:
    fixture_root = Path("contracts/local_product/fixtures")
    pairs = [
        ("platform_evidence_harvest.schema.json", "harvest_blocked_auth.json"),
        ("source_install_rc_claim.schema.json", "source_install_claim_pass_partial.json"),
        ("source_install_rc_claim.schema.json", "source_install_claim_fail_overclaim.json"),
    ]
    for schema_name, fixture_name in pairs:
        Draft202012Validator(_schema(schema_name)).validate(
            json.loads((fixture_root / fixture_name).read_text(encoding="utf-8"))
        )
    action_schema = _schema("target_closure_action.schema.json")
    for action in json.loads(
        (fixture_root / "target_closure_actions_partial.json").read_text(encoding="utf-8")
    ):
        Draft202012Validator(action_schema).validate(action)

