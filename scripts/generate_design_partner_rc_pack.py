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
from binliquid.control_plane.design_partner_rc import (
    build_design_partner_rc_status,
    is_expected_blocked_claim_boundary_alert,
)
from binliquid.control_plane.pilot_operations import build_design_partner_beta_status
from binliquid.control_plane.snapshot import build_control_plane_snapshot
from binliquid.runtime.config import RuntimeConfig


REQUIRED_OPTIONAL_ARTIFACTS = [
    "external_gateway_smoke.json",
    "policy_pack_promotion.json",
    "evidence_index.json",
    "reports-alerts-logs/manifest.json",
    "control-plane-snapshot.json",
    "claim-guard-matrix.json",
    "design-partner-rc-status.json",
    "DESIGN_PARTNER_RC_REPORT.md",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Design Partner RC release pack.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--output", default="artifacts/design-partner-rc")
    parser.add_argument("--state-root", default=".binliquid/control-plane")
    parser.add_argument("--evidence-root", default="artifacts")
    parser.add_argument("--beta-evidence-root")
    parser.add_argument("--fail-on-conditional", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    output = REPO_ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC)
    config = RuntimeConfig.from_profile(args.profile)
    state_root = _resolve_path(args.state_root)
    evidence_root = _resolve_path(args.evidence_root)
    beta_evidence_root = (
        _resolve_path(args.beta_evidence_root) if args.beta_evidence_root else evidence_root
    )

    snapshot = build_control_plane_snapshot(
        root_dir=state_root,
        profile=args.profile,
        evidence_root=evidence_root,
        runtime_mode="cli",
        bridge_mode="cli",
        used_fixture=False,
    )
    claim_matrix = ClaimGuard(config=config).evaluate(evidence_root=evidence_root)
    beta_status = build_design_partner_beta_status(
        evidence_root=beta_evidence_root,
        generated_at=snapshot.generated_at_utc,
    )
    snapshot.design_partner_beta = beta_status
    snapshot.design_partner_rc = build_design_partner_rc_status(
        data_source=snapshot.data_source,
        claims=claim_matrix.model_dump(mode="json"),
        evidence_packs=snapshot.evidence_packs,
        reports=snapshot.reports,
        alerts=snapshot.alerts,
        execution_surfaces=snapshot.execution_surfaces,
        design_partner_beta=beta_status,
        generated_at=snapshot.generated_at_utc,
    )

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

    initial_manifest = {
        "version": "control-plane.design-partner-rc-pack/v1",
        "generatedAtUtc": generated_at.isoformat(),
        "status": "pending",
        "output": _display_path(output),
        "profile": args.profile,
        "stateRoot": _display_path(state_root),
        "evidenceRoot": _display_path(evidence_root),
        "designPartnerRcStatus": snapshot.design_partner_rc.status,
        "blockers": list(snapshot.design_partner_rc.blockers),
        "warnings": list(snapshot.design_partner_rc.warnings),
        "artifacts": [],
        "claimBoundaries": _claim_boundaries(snapshot),
        "evidencePackCount": len(snapshot.evidence_packs),
        "readyReportCount": sum(1 for report in snapshot.reports if report.status == "ready"),
        "activeErrorAlertCount": _active_error_alert_count(snapshot),
    }
    _write_report(output / "DESIGN_PARTNER_RC_REPORT.md", initial_manifest)

    artifacts = _artifact_status(output)
    artifact_blockers = [
        f"artifact:{item['path']}"
        for item in artifacts
        if item.get("status") in {"blocked", "fail", "failed"}
    ]
    artifact_warnings = [
        f"artifact:{item['path']}"
        for item in artifacts
        if item.get("status") in {"conditional", "missing"}
    ]
    blockers = [*snapshot.design_partner_rc.blockers, *artifact_blockers]
    warnings = [*snapshot.design_partner_rc.warnings, *artifact_warnings]
    status = (
        "blocked"
        if blockers
        else "conditional"
        if warnings
        else "pass"
    )
    manifest = {
        "version": "control-plane.design-partner-rc-pack/v1",
        "generatedAtUtc": generated_at.isoformat(),
        "status": status,
        "output": _display_path(output),
        "profile": args.profile,
        "stateRoot": _display_path(state_root),
        "evidenceRoot": _display_path(evidence_root),
        "designPartnerRcStatus": snapshot.design_partner_rc.status,
        "blockers": blockers,
        "warnings": warnings,
        "artifacts": artifacts,
        "claimBoundaries": _claim_boundaries(snapshot),
        "evidencePackCount": len(snapshot.evidence_packs),
        "readyReportCount": sum(1 for report in snapshot.reports if report.status == "ready"),
        "activeErrorAlertCount": _active_error_alert_count(snapshot),
    }
    _write_json(output / "manifest.json", manifest)
    _write_report(output / "DESIGN_PARTNER_RC_REPORT.md", manifest)
    if args.json:
        print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"built {output}")
    if status == "blocked" or (args.fail_on_conditional and status == "conditional"):
        raise SystemExit(1)


def _artifact_status(output: Path) -> list[dict[str, object]]:
    items = []
    for relative in REQUIRED_OPTIONAL_ARTIFACTS:
        path = output / relative
        present = path.exists()
        size = path.stat().st_size if present else 0
        items.append(
            {
                "path": relative,
                "present": present,
                "bytes": size,
                "sourcePath": _display_path(path) if present else None,
                "status": _artifact_payload_status(path) if present and size > 0 else "missing",
            }
        )
    return items


def _artifact_payload_status(path: Path) -> str:
    if path.suffix.lower() != ".json":
        return "present"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "blocked"
    if not isinstance(payload, dict):
        return "present"
    status = payload.get("status")
    if isinstance(status, str):
        return status
    design_partner_rc = payload.get("designPartnerRc")
    if isinstance(design_partner_rc, dict) and isinstance(design_partner_rc.get("status"), str):
        return str(design_partner_rc["status"])
    return "present"


def _write_report(path: Path, manifest: dict[str, object]) -> None:
    lines = [
        "# Design Partner RC Report",
        "",
        f"Status: {manifest['status']}",
        f"Generated: {manifest['generatedAtUtc']}",
        f"Profile: {manifest.get('profile')}",
        f"Evidence root: {manifest.get('evidenceRoot')}",
        f"State root: {manifest.get('stateRoot')}",
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
            lines.append(
                f"- {item['path']}: {item.get('status')} "
                f"({'present' if item['present'] else 'missing'}, {item.get('bytes')} bytes)"
            )
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


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _claim_boundaries(snapshot: object) -> dict[str, str]:
    surfaces = getattr(snapshot, "execution_surfaces", [])
    return {
        "computerUseLive": _surface_status(surfaces, "computer-use"),
        "publicDesktopInstaller": _surface_status(surfaces, "public-desktop-installer"),
    }


def _surface_status(surfaces: object, surface_id: str) -> str:
    if not isinstance(surfaces, list):
        return "missing"
    for surface in surfaces:
        if getattr(surface, "surface_id", None) == surface_id:
            return str(getattr(surface, "status", "missing"))
    return "missing"


def _active_error_alert_count(snapshot: object) -> int:
    alerts = getattr(snapshot, "alerts", [])
    if not isinstance(alerts, list):
        return 0
    return sum(
        1
        for alert in alerts
        if getattr(alert, "status", None) == "active"
        and getattr(alert, "severity", None) in {"error", "critical"}
        and not is_expected_blocked_claim_boundary_alert(alert)
    )


if __name__ == "__main__":
    main()
