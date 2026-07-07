from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from binliquid.local_product.evidence_bundle import export_platform_evidence_bundle
from binliquid.local_product.evidence_collector import collect_platform_evidence
from binliquid.local_product.evidence_importer import import_platform_evidence_bundle
from binliquid.local_product.evidence_reconciler import reconcile_platform_evidence
from binliquid.local_product.rc_handoff import build_local_product_rc_handoff


def _load_schema(name: str) -> dict[str, object]:
    return json.loads((Path("contracts/local_product") / name).read_text(encoding="utf-8"))


def test_local_product_evidence_contract_schemas_are_generated() -> None:
    subprocess.run(
        [sys.executable, "scripts/generate_local_product_evidence_contract_schemas.py"],
        check=True,
    )

    assert (Path("contracts/local_product") / "platform_evidence_manifest.schema.json").exists()
    assert (Path("contracts/local_product") / "platform_rc_handoff_manifest.schema.json").exists()


def test_local_product_evidence_contracts_validate_payloads(tmp_path: Path) -> None:
    manifest = collect_platform_evidence(
        profile="enterprise",
        target="windows-x64",
        output_root=tmp_path / "evidence",
    )
    bundle = export_platform_evidence_bundle(
        manifest_path=tmp_path / "evidence" / "platform_evidence_manifest.json",
        bundle_path=tmp_path / "bundle.zip",
    )
    import_platform_evidence_bundle(
        bundle_path=tmp_path / "bundle.zip",
        store_root=tmp_path / "store",
    )
    reconciliation = reconcile_platform_evidence(store_root=tmp_path / "store")
    handoff = build_local_product_rc_handoff(
        profile="enterprise",
        evidence_root=tmp_path / "store",
        output_root=tmp_path / "handoff",
    )

    Draft202012Validator(_load_schema("platform_evidence_manifest.schema.json")).validate(
        manifest.model_dump(mode="json", by_alias=True)
    )
    Draft202012Validator(_load_schema("platform_evidence_bundle.schema.json")).validate(
        bundle.model_dump(mode="json", by_alias=True)
    )
    Draft202012Validator(_load_schema("platform_evidence_reconciliation.schema.json")).validate(
        reconciliation.model_dump(mode="json", by_alias=True)
    )
    Draft202012Validator(_load_schema("platform_rc_handoff_manifest.schema.json")).validate(
        handoff.model_dump(mode="json", by_alias=True)
    )


def test_local_product_evidence_contract_fixtures_validate() -> None:
    fixture_root = Path("contracts/local_product/fixtures")
    fixture_pairs = [
        (
            "platform_evidence_manifest.schema.json",
            "platform_evidence_manifest_windows_x64_pass.json",
        ),
        (
            "platform_evidence_reconciliation.schema.json",
            "platform_evidence_reconciliation_pass.json",
        ),
        (
            "platform_evidence_reconciliation.schema.json",
            "platform_evidence_reconciliation_claim_without_evidence_fail.json",
        ),
    ]
    for schema_name, fixture_name in fixture_pairs:
        Draft202012Validator(_load_schema(schema_name)).validate(
            json.loads((fixture_root / fixture_name).read_text(encoding="utf-8"))
        )
