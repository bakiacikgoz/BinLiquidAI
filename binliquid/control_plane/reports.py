from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from binliquid.control_plane.models import (
    AlertEvaluation,
    AlertSummary,
    ControlPlaneSnapshot,
    ReportManifest,
    ReportManifestItem,
)


def build_reports_alerts_logs_manifest(
    *,
    snapshot: ControlPlaneSnapshot,
    output_dir: str | Path = "artifacts/design-partner-rc/reports-alerts-logs",
) -> ReportManifest:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC)

    reports = [
        _write_report(
            root=root,
            report_id="claim-guard-summary",
            kind="readiness",
            title="Claim guard summary",
            status=snapshot.design_partner_rc.status,
            generated_at=generated_at,
            payload={
                "designPartnerRc": snapshot.design_partner_rc.model_dump(
                    mode="json",
                    by_alias=True,
                ),
                "partialReasons": snapshot.partial_reasons,
            },
        ),
        _write_report(
            root=root,
            report_id="policy-compliance",
            kind="policy",
            title="Policy compliance",
            status="ready" if snapshot.policy_packs else "missing",
            generated_at=generated_at,
            payload={
                "policyPacks": [
                    item.model_dump(mode="json", by_alias=True)
                    for item in snapshot.policy_packs
                ]
            },
        ),
        _write_report(
            root=root,
            report_id="approval-latency",
            kind="metrics",
            title="Approval latency",
            status="ready" if snapshot.approvals else "conditional",
            generated_at=generated_at,
            payload={
                "approvals": [
                    item.model_dump(mode="json", by_alias=True)
                    for item in snapshot.approvals
                ]
            },
        ),
        _write_report(
            root=root,
            report_id="evidence-verification",
            kind="evidence",
            title="Evidence verification",
            status="ready" if snapshot.evidence_packs else "conditional",
            generated_at=generated_at,
            payload={
                "evidencePacks": [
                    item.model_dump(mode="json", by_alias=True)
                    for item in snapshot.evidence_packs
                ]
            },
        ),
    ]
    alert_evaluations = [
        _alert_evaluation(alert, generated_at=generated_at) for alert in snapshot.alerts
    ]
    logs_ref = _write_logs(root=root, snapshot=snapshot, generated_at=generated_at)
    blocking_reasons = [
        alert.reason_code
        for alert in alert_evaluations
        if alert.state == "active" and alert.severity == "critical"
    ]
    warnings = [
        alert.reason_code
        for alert in alert_evaluations
        if alert.state == "active" and alert.severity == "warning"
    ]
    status = "blocked" if blocking_reasons else "conditional" if warnings else "pass"
    manifest = ReportManifest(
        status=status,
        reports=reports,
        alerts=alert_evaluations,
        logs_export_ref=logs_ref,
        blocking_reasons=blocking_reasons,
        warnings=warnings,
    )
    (root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return manifest


def _write_report(
    *,
    root: Path,
    report_id: str,
    kind: str,
    title: str,
    status: str,
    generated_at: datetime,
    payload: dict[str, Any],
) -> ReportManifestItem:
    path = root / f"{report_id}.json"
    payload = {
        "version": "control-plane.report/v1",
        "reportId": report_id,
        "title": title,
        "status": status,
        "generatedAtUtc": generated_at.isoformat(),
        **payload,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return ReportManifestItem(
        report_id=report_id,
        kind=kind,
        title=title,
        status=status,
        path=str(path),
        generated_at_utc=generated_at,
        summary=f"{title}: {status}",
    )


def _alert_evaluation(alert: AlertSummary, *, generated_at: datetime) -> AlertEvaluation:
    severity = (
        "critical"
        if alert.severity == "critical"
        else "warning"
        if alert.severity == "error"
        else alert.severity
    )
    return AlertEvaluation(
        alert_id=alert.alert_id,
        severity=severity,
        state="active" if alert.status == "active" else "resolved",
        source="snapshot",
        reason_code=alert.reason_code,
        suggested_action=alert.recommended_action,
        first_seen_at=generated_at,
        last_seen_at=generated_at,
    )


def _write_logs(*, root: Path, snapshot: ControlPlaneSnapshot, generated_at: datetime) -> str:
    relative = "logs_timeline.json"
    path = root / relative
    path.write_text(
        json.dumps(
            {
                "version": "control-plane.logs-export/v1",
                "generatedAtUtc": generated_at.isoformat(),
                "events": [item.model_dump(mode="json", by_alias=True) for item in snapshot.logs],
                "redactionSummary": {
                    "rawPayloadsIncluded": False,
                    "secretsRedacted": True,
                },
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return str(path)
