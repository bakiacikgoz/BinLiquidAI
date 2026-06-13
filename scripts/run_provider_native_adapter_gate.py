from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.control_plane.provider_conformance import run_provider_native_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline native provider conformance gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output-dir", default="artifacts/provider-native")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    payload = run_provider_native_gate(profile=args.profile, output_dir=args.output_dir)
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload['status']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
