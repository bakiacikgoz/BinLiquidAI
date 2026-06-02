from __future__ import annotations

# ruff: noqa: E402, I001

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from binliquid.control_plane.claim_guard import ClaimGuard
from binliquid.control_plane.snapshot import build_control_plane_snapshot
from binliquid.runtime.config import RuntimeConfig


REQUIRED_OPTIONAL_ARTIFACTS = [
    "external_gateway_smoke.json",
    "policy_pack_promotion.json",
    "evidence_index.json",
    "reports-alerts-logs/manifest.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Design Partner RC release pack.")
    parser.add_argument("--profile", default="lite")
    parser.add_argument("--output", default="artifacts/design-partner-rc")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = REPO_ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    config = RuntimeConfig.from_profile(args.profile)
    state_root = output / "state" / "control-plane"
    evidence_root = output / "evidence-sample"

    snapshot = build_control_plane_snapshot(
        root_dir=state_root,
        profile=args.profile,
        evidence_root=evidence_root,
        runtime_mode="cli",
        bridge_mode="cli",
        used_fixture=False,
    )
    claim_matrix = ClaimGuard(config=config).evaluate(evidence_root=evidence_root)

    _write_json(
        output / "control-plane-snapshot.json",
        snapshot.model_dump(mode="json", by_alias=True),
    )
    _write_json(output / "claim-guard-matrix.json", claim_matrix.model_dump(mode="json"))
    _write_json(
        output / "design-partner-rc-status.json",
        snapshot.design_partner_rc.model_dump(mode="json", by_alias=True),
    )
    _write_text(output / "head_commit.txt", _git(["rev-parse", "HEAD"]))
    _write_text(output / "git_status.txt", _git(["status", "--short"]))

    artifacts = _artifact_status(output)
    blockers = list(snapshot.design_partner_rc.blockers)
    status = (
        "blocked"
        if blockers
        else "conditional"
        if snapshot.design_partner_rc.warnings
        else "pass"
    )
    manifest = {
        "version": "control-plane.design-partner-rc-pack/v1",
        "generatedAtUtc": datetime.now(UTC).isoformat(),
        "status": status,
        "output": _display_path(output),
        "profile": args.profile,
        "designPartnerRcStatus": snapshot.design_partner_rc.status,
        "blockers": blockers,
        "warnings": snapshot.design_partner_rc.warnings,
        "artifacts": artifacts,
        "claimBoundaries": {
            "computerUseLive": "blocked",
            "publicDesktopInstaller": "blocked",
        },
    }
    _write_json(output / "manifest.json", manifest)
    _write_report(output / "DESIGN_PARTNER_RC_REPORT.md", manifest)
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"built {output}")
    if status == "blocked":
        raise SystemExit(1)


def _artifact_status(output: Path) -> list[dict[str, object]]:
    items = []
    for relative in REQUIRED_OPTIONAL_ARTIFACTS:
        path = output / relative
        items.append(
            {
                "path": relative,
                "present": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return items


def _write_report(path: Path, manifest: dict[str, object]) -> None:
    lines = [
        "# Design Partner RC Report",
        "",
        f"Status: {manifest['status']}",
        f"Generated: {manifest['generatedAtUtc']}",
        "",
        "## Boundary",
        "",
        "- Computer-use live execution remains blocked.",
        "- Public desktop installer claim remains blocked.",
        "- Preview fixtures are not treated as live evidence.",
        "",
        "## Artifacts",
        "",
    ]
    for item in manifest["artifacts"]:
        if isinstance(item, dict):
            lines.append(f"- {item['path']}: {'present' if item['present'] else 'missing'}")
    lines.extend(["", "## Warnings", ""])
    warnings = manifest.get("warnings") if isinstance(manifest, dict) else []
    if isinstance(warnings, list) and warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def _git(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return proc.stdout if proc.returncode == 0 else proc.stderr


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
