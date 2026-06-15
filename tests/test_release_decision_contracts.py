from __future__ import annotations

import json
from pathlib import Path


def test_release_decision_contract_schemas_exist() -> None:
    root = Path("contracts/release_decision")
    expected = {
        "rc_freeze_reconciliation.schema.json",
        "no_ship_register.schema.json",
        "human_signoff.schema.json",
        "release_decision_dossier.schema.json",
    }

    assert expected <= {path.name for path in root.glob("*.schema.json")}


def test_release_decision_fixtures_validate_shape() -> None:
    root = Path("contracts/release_decision/fixtures")
    for path in root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert "schemaVersion" in payload
