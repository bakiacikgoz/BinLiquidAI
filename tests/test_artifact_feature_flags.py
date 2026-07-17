from __future__ import annotations

import json
from pathlib import Path

from imperaos.artifacts.feature_flags import (
    ARTIFACT_FEATURE_FLAG_NAMES,
    resolve_artifact_feature_flags,
)


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
