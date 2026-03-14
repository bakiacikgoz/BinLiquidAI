from __future__ import annotations

import json
from pathlib import Path

from binliquid.contracts.operator_panel import (
    ApprovalDetailPayloadContract,
    ApprovalPendingPayloadContract,
    AuthCheckPayloadContract,
    AuthWhoAmIPayloadContract,
    BridgeHandshakeContract,
    ConfigResolvePayloadContract,
    DeviceActionApprovalSnapshotContract,
    KeyStatusPayloadContract,
    OperatorCapabilitiesPayload,
    PreviewFixtureBundleContract,
    ReadArtifactPayloadContract,
    RunReplayPayloadContract,
    RunSummaryPayloadContract,
    SecurityBaselinePayloadContract,
    SpawnedRunPayloadContract,
    SupportBundleExportPayloadContract,
    TailEventsPayloadContract,
    TeamStatusArtifactContract,
)

SCHEMAS = {
    "approval_detail": ApprovalDetailPayloadContract,
    "approval_pending": ApprovalPendingPayloadContract,
    "auth_check": AuthCheckPayloadContract,
    "auth_whoami": AuthWhoAmIPayloadContract,
    "bridge_handshake": BridgeHandshakeContract,
    "config_resolve": ConfigResolvePayloadContract,
    "device_action_snapshot": DeviceActionApprovalSnapshotContract,
    "key_status": KeyStatusPayloadContract,
    "operator_capabilities": OperatorCapabilitiesPayload,
    "preview_fixture_bundle": PreviewFixtureBundleContract,
    "read_artifact": ReadArtifactPayloadContract,
    "run_replay": RunReplayPayloadContract,
    "run_summary": RunSummaryPayloadContract,
    "security_baseline": SecurityBaselinePayloadContract,
    "spawned_run": SpawnedRunPayloadContract,
    "support_bundle_export": SupportBundleExportPayloadContract,
    "tail_events": TailEventsPayloadContract,
    "team_status_artifact": TeamStatusArtifactContract,
}


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "contracts" / "operator_panel" / "schemas"
    root.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        target = root / f"{name}.schema.json"
        target.write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
