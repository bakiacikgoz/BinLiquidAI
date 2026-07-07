from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_product_contract_fixtures_validate_against_schemas() -> None:
    subprocess.run(
        [sys.executable, "scripts/generate_local_product_contract_schemas.py"],
        cwd=REPO_ROOT,
        check=True,
    )
    schema_root = REPO_ROOT / "contracts" / "local_product"
    validators = {
        "platform_target": Draft202012Validator(
            json.loads((schema_root / "platform_target.schema.json").read_text(encoding="utf-8"))
        ),
        "local_environment_probe": Draft202012Validator(
            json.loads(
                (schema_root / "local_environment_probe.schema.json").read_text(
                    encoding="utf-8"
                )
            )
        ),
        "local_product_readiness_report": Draft202012Validator(
            json.loads(
                (schema_root / "local_product_readiness_report.schema.json").read_text(
                    encoding="utf-8"
                )
            )
        ),
        "local_product_claim_boundary": Draft202012Validator(
            json.loads(
                (schema_root / "local_product_claim_boundary.schema.json").read_text(
                    encoding="utf-8"
                )
            )
        ),
    }

    for path in (schema_root / "fixtures").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        validator_key = payload["fixtureSchema"]
        validators[validator_key].validate(payload["payload"])

    leak = json.loads((schema_root / "fixtures" / "raw_secret_leak_fail.json").read_text())
    assert leak["expectedStatus"] == "fail"
    assert leak["payload"]["secretScanStatus"] == "fail"

