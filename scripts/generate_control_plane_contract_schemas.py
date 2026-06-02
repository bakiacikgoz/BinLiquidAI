from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.control_plane.models import (  # noqa: E402
    ActionProposal,
    AgentRecord,
    AgentRegistryV2Snapshot,
    AgentSpec,
    ClaimMatrix,
    ControlPlaneRunSummary,
    ControlPlaneSnapshot,
    EvidencePackManifest,
    EvidenceVerifyResult,
    PolicyPackDiffResult,
    PolicyPackManifest,
    PolicyPackPromotionDryRun,
    PolicySimulationResult,
    ReadinessReport,
)
from binliquid.control_plane.external_contracts import (  # noqa: E402
    ExternalActionRequest,
    ExternalActionResponse,
)

SCHEMAS = {
    "agent_spec": AgentSpec,
    "agent_record": AgentRecord,
    "agent_registry_v2": AgentRegistryV2Snapshot,
    "action_proposal": ActionProposal,
    "policy_simulation": PolicySimulationResult,
    "policy_pack_manifest": PolicyPackManifest,
    "policy_pack_diff": PolicyPackDiffResult,
    "policy_pack_promotion": PolicyPackPromotionDryRun,
    "control_plane_run_summary": ControlPlaneRunSummary,
    "evidence_pack_manifest": EvidencePackManifest,
    "evidence_verify_result": EvidenceVerifyResult,
    "readiness_report": ReadinessReport,
    "claim_matrix": ClaimMatrix,
    "control_plane_snapshot": ControlPlaneSnapshot,
    "external_agent_request": ExternalActionRequest,
    "external_agent_response": ExternalActionResponse,
}

OPERATOR_PANEL_SCHEMAS = {
    "control_plane_snapshot": ControlPlaneSnapshot,
}


def main() -> None:
    root = REPO_ROOT / "contracts" / "control_plane"
    root.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (root / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    operator_root = REPO_ROOT / "contracts" / "operator_panel" / "schemas"
    operator_root.mkdir(parents=True, exist_ok=True)
    for name, model in OPERATOR_PANEL_SCHEMAS.items():
        (operator_root / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
