from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from binliquid.model_providers.native.conformance import (
    run_openai_responses_native_conformance,
    verify_native_conformance_evidence,
    write_native_conformance_report,
)


def run_provider_native_adapter_gate(
    *,
    profile: str,
    output_root: Path,
) -> dict[str, Any]:
    report = run_openai_responses_native_conformance(profile=profile)
    paths = write_native_conformance_report(report=report, output_root=output_root)
    verify = verify_native_conformance_evidence(output_root=output_root)
    status = "pass" if report.status == "pass" and verify["status"] == "pass" else "fail"
    gate = {
        "version": "model_provider.native_adapter_gate/v1",
        "status": status,
        "profile": profile,
        "liveCanaryAttempted": False,
        "nativeConformance": report.model_dump(mode="json"),
        "evidenceVerify": verify,
        "paths": paths,
    }
    gate_path = output_root / "provider_native_adapter_gate.json"
    gate_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return gate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run provider native adapter V2 gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("artifacts/model-provider-governance/native-v2"),
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    gate = run_provider_native_adapter_gate(profile=args.profile, output_root=args.output_root)
    if args.json_output:
        print(json.dumps(gate, indent=2, sort_keys=True))
    else:
        print(f"status={gate['status']} profile={gate['profile']}")
    return 0 if gate["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
