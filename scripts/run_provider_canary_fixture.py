from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.generate_provider_canary_evidence import generate_canary_evidence
except ModuleNotFoundError:
    from generate_provider_canary_evidence import generate_canary_evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run offline provider canary fixtures.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/model-provider-governance/canary"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = generate_canary_evidence(profile=args.profile, output_dir=args.output_dir)
    payload = {
        "version": "model_provider.canary_fixture_gate/v1",
        "status": result["verify"]["status"],
        "reasonCode": result["verify"]["reasonCode"],
        "outputDir": str(args.output_dir),
        "files": sorted(path.name for path in args.output_dir.glob("*.json")),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={payload['status']} reason={payload['reasonCode']}")
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
