from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.local_product.cli import build_matrix_report, build_readiness_report  # noqa: E402

DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "local-product-readiness"


def run_local_product_readiness_gate(
    *,
    profile: str = "enterprise",
    target_value: str = "auto",
    matrix: bool = False,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    json_output: bool = False,
    run_product_closure: bool = True,
) -> dict[str, Any]:
    del json_output, run_product_closure
    if matrix:
        return build_matrix_report(profile=profile, include_experimental=True)
    return build_readiness_report(
        profile=profile,
        target_value=target_value,
        output_root=output_root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local product readiness gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--target", default="auto")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    report = run_local_product_readiness_gate(
        profile=args.profile,
        target_value=args.target,
        matrix=args.matrix,
        output_root=args.output_root,
        json_output=args.json_output,
    )
    if args.json_output:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report.get('overallStatus', report.get('schemaVersion'))}")
    return 0 if report.get("overallStatus", "pass") in {"pass", "conditional"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

