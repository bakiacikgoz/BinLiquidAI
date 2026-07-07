from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.artifact_sources import (  # noqa: E402
    PlatformEvidenceHarvestReport,
    RemoteArtifactSource,
)
from binliquid.local_product.source_install_claim import SourceInstallRcClaim  # noqa: E402
from binliquid.local_product.target_closure import TargetClosureAction  # noqa: E402

SCHEMA_ROOT = REPO_ROOT / "contracts" / "local_product"

SCHEMAS = {
    "remote_artifact_source.schema.json": RemoteArtifactSource,
    "platform_evidence_harvest.schema.json": PlatformEvidenceHarvestReport,
    "source_install_rc_claim.schema.json": SourceInstallRcClaim,
    "target_closure_action.schema.json": TargetClosureAction,
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

