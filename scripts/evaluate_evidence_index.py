from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.control_plane.evidence_index import build_evidence_index
from binliquid.runtime.config import RuntimeConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate control-plane evidence index.")
    parser.add_argument("--profile", default="lite")
    parser.add_argument("--evidence-root", default="artifacts/design-partner-rc/evidence-sample")
    parser.add_argument("--root-dir", default="artifacts/design-partner-rc/evidence-index/state")
    parser.add_argument("--output", default="artifacts/design-partner-rc/evidence_index.json")
    args = parser.parse_args()

    index = build_evidence_index(
        config=RuntimeConfig.from_profile(args.profile),
        evidence_root=REPO_ROOT / args.evidence_root,
        root_dir=REPO_ROOT / args.root_dir,
    )
    payload = index.model_dump(mode="json", by_alias=True)
    output = REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    if index.status == "blocked":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
