from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.evidence_models import (  # noqa: E402
    HostProbe,
    PlatformEvidenceBundleSummary,
    PlatformEvidenceManifest,
    PlatformEvidenceReconciliation,
    PlatformEvidenceVerification,
    PlatformRCHandoffManifest,
)

SCHEMA_ROOT = REPO_ROOT / "contracts" / "local_product"

SCHEMAS = {
    "host_probe.schema.json": HostProbe,
    "platform_evidence_manifest.schema.json": PlatformEvidenceManifest,
    "platform_evidence_bundle.schema.json": PlatformEvidenceBundleSummary,
    "platform_evidence_verification.schema.json": PlatformEvidenceVerification,
    "platform_evidence_reconciliation.schema.json": PlatformEvidenceReconciliation,
    "platform_rc_handoff_manifest.schema.json": PlatformRCHandoffManifest,
}


def main() -> int:
    SCHEMA_ROOT.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (SCHEMA_ROOT / name).write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
