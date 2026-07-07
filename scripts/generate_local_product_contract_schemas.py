from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.fixtures import contract_fixtures  # noqa: E402
from binliquid.local_product.models import (  # noqa: E402
    LocalEnvironmentProbe,
    LocalProductClaimBoundary,
    LocalProductReadinessReport,
    PlatformTarget,
)

SCHEMAS = {
    "platform_target": PlatformTarget,
    "local_environment_probe": LocalEnvironmentProbe,
    "local_product_readiness_report": LocalProductReadinessReport,
    "local_product_claim_boundary": LocalProductClaimBoundary,
}


def main() -> None:
    root = REPO_ROOT / "contracts" / "local_product"
    root.mkdir(parents=True, exist_ok=True)
    for name, model in SCHEMAS.items():
        (root / f"{name}.schema.json").write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    fixture_root = root / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=True)
    for name, payload in contract_fixtures().items():
        (fixture_root / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()

