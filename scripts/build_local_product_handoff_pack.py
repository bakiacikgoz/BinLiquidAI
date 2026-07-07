from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_local_product_readiness_gate import run_local_product_readiness_gate  # noqa: E402


def build_local_product_handoff_pack(
    *,
    profile: str = "enterprise",
    output_root: Path = REPO_ROOT / "artifacts" / "local-product-handoff",
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    readiness = run_local_product_readiness_gate(
        profile=profile,
        output_root=output_root / "readiness",
        run_product_closure=False,
    )
    matrix = run_local_product_readiness_gate(
        profile=profile,
        matrix=True,
        output_root=output_root / "matrix",
        run_product_closure=False,
    )
    pack = {
        "schemaVersion": "local_product_handoff_pack/v1",
        "profile": profile,
        "readiness": readiness,
        "platformMatrix": matrix,
        "claimBoundary": matrix.get("productClaimSummary"),
        "setupNotes": [
            (
                "Run uv run python scripts/run_local_product_readiness_gate.py "
                "--profile enterprise --json"
            ),
            (
                "Run uv run python scripts/run_local_product_readiness_gate.py "
                "--profile enterprise --matrix --json"
            ),
        ],
    }
    (output_root / "local_product_handoff_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local product handoff pack.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "artifacts" / "local-product-handoff",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    pack = build_local_product_handoff_pack(profile=args.profile, output_root=args.output_root)
    if args.json_output:
        print(json.dumps(pack, indent=2, sort_keys=True))
    else:
        print(f"handoff={args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
