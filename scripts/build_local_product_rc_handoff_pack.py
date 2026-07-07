from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.evidence_importer import DEFAULT_EVIDENCE_STORE  # noqa: E402
from binliquid.local_product.rc_handoff import build_local_product_rc_handoff  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local product RC handoff pack.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--evidence-root", type=Path, default=DEFAULT_EVIDENCE_STORE)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT / "artifacts" / "local-product-rc-handoff",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    manifest = build_local_product_rc_handoff(
        profile=args.profile,
        evidence_root=args.evidence_root,
        output_root=args.output_root,
    )
    payload = manifest.model_dump(mode="json", by_alias=True)
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"manifest={args.output_root / 'manifest.json'}")
    return 0 if manifest.status != "blocked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
