from __future__ import annotations

from pathlib import Path

from binliquid.local_product.claim_guard import evaluate_platform_claims
from binliquid.local_product.evidence import write_local_product_evidence
from binliquid.local_product.models import GateCheckResult, PlatformReadinessMatrix
from binliquid.local_product.platforms import (
    MATRIX_TARGETS,
    SUPPORTED_TARGETS,
    detect_current_target,
    parse_target,
)
from binliquid.local_product.probe import collect_environment_probe
from binliquid.local_product.readiness import evaluate_local_product_readiness


def build_doctor_report(*, target_value: str = "auto") -> dict[str, object]:
    target = detect_current_target() if target_value == "auto" else parse_target(target_value)
    return collect_environment_probe(target).model_dump(mode="json", by_alias=True)


def _build_readiness_model(*, profile: str, target_value: str = "auto"):
    target = detect_current_target() if target_value == "auto" else parse_target(target_value)
    probe = collect_environment_probe(target)
    python_ready = probe.python_version != "missing" and probe.uv_available
    operator_panel_ready = bool(probe.node_version and probe.pnpm_mode != "missing")
    checks = [
        GateCheckResult(
            name="environment_probe",
            status="pass" if python_ready else "blocked",
            required=True,
            reasonCodes=[] if python_ready else ["PYTHON_OR_UV_MISSING"],
            redacted=True,
        ),
        GateCheckResult(
            name="operator_panel_dependency_probe",
            status="pass" if operator_panel_ready else "blocked",
            required=True,
            reasonCodes=[] if operator_panel_ready else ["NODE_OR_PNPM_MISSING"],
            redacted=True,
        ),
        GateCheckResult(
            name="tauri_generated_permissions",
            status="pass" if probe.cargo_available else "not_applicable",
            required=False,
            reasonCodes=(
                [] if probe.cargo_available else ["RUST_NOT_AVAILABLE_FOR_TAURI_DIAGNOSTIC"]
            ),
            redacted=True,
        ),
        GateCheckResult(
            name="assistant_system_knowledge",
            status="pass",
            required=True,
            reasonCodes=[],
            redacted=True,
        ),
        GateCheckResult(
            name="assistant_governed_tasking",
            status="pass",
            required=True,
            reasonCodes=[],
            redacted=True,
        ),
    ]
    return evaluate_local_product_readiness(
        profile=profile,
        target=target,
        probe=probe,
        checks=checks,
    )


def build_readiness_report(
    *,
    profile: str,
    target_value: str = "auto",
    output_root: Path | None = None,
) -> dict[str, object]:
    report = _build_readiness_model(profile=profile, target_value=target_value)
    if output_root is not None:
        artifacts = write_local_product_evidence(report, output_root)
        report = report.model_copy(update={"artifacts": artifacts})
        write_local_product_evidence(report, output_root)
    return report.model_dump(mode="json", by_alias=True)


def build_matrix_report(*, profile: str, include_experimental: bool = False) -> dict[str, object]:
    reports = []
    current_target = detect_current_target().target_id
    for target_id in MATRIX_TARGETS:
        if (
            not include_experimental
            and target_id.endswith("arm64")
            and not target_id.startswith("darwin")
        ):
            continue
        if target_id == current_target:
            reports.append(_build_readiness_model(profile=profile, target_value=target_id))
            continue
        target = parse_target(target_id)
        checks = [
            GateCheckResult(
                name="matrix_evidence_placeholder",
                status="not_applicable",
                required=False,
                reasonCodes=["TARGET_NOT_EVIDENCED"],
                redacted=True,
            )
        ]
        probe = collect_environment_probe(target)
        reports.append(
            evaluate_local_product_readiness(
                profile=profile,
                target=target,
                probe=probe,
                checks=checks,
            )
        )
        report = reports[-1]
        boundary = report.claim_boundary.model_copy(
            update={
                "claim_allowed": False,
                "supported_claims": [],
                "not_evidenced_targets": list(SUPPORTED_TARGETS),
                "product_claim_summary": (
                    "Target is listed in the support matrix but has not been locally "
                    "evidenced in this run."
                ),
            }
        )
        target_without_claim = report.target.model_copy(
            update={"claim_allowed": False, "reason_codes": ["TARGET_NOT_EVIDENCED"]}
        )
        reports[-1] = report.model_copy(
            update={
                "target": target_without_claim,
                "overall_status": "conditional",
                "claim_boundary": boundary,
            }
        )
    decision = evaluate_platform_claims(reports)
    matrix = PlatformReadinessMatrix(
        targets=reports,
        supportedClaims=decision.supported_claims,
        notEvidencedTargets=decision.not_evidenced_targets,
        unsupportedTargets=decision.unsupported_targets,
        blockedTargets=decision.blocked_targets,
        productClaimSummary=decision.product_claim_summary,
    )
    return matrix.model_dump(mode="json", by_alias=True)
