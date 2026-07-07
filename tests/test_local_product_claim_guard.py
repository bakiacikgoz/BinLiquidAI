from __future__ import annotations

from binliquid.local_product.claim_guard import evaluate_platform_claims
from binliquid.local_product.models import GateCheckResult, LocalEnvironmentProbe
from binliquid.local_product.platforms import parse_target
from binliquid.local_product.readiness import evaluate_local_product_readiness


def _passing_report(target_id: str):
    target = parse_target(target_id)
    probe = LocalEnvironmentProbe(
        target=target,
        pythonVersion="Python 3.11.9",
        uvAvailable=True,
        nodeVersion="v22.12.0",
        pnpmMode="local_bin",
        rustcVersion="rustc 1.88.0",
        cargoAvailable=True,
        tauriCliAvailable=False,
        webviewStatus="available",
        pathStyle="windows" if target.os == "windows" else "posix",
        newlineMode="unknown",
        detectedAt="2026-07-07T00:00:00Z",
    )
    return evaluate_local_product_readiness(
        profile="enterprise",
        target=target,
        probe=probe,
        checks=[
            GateCheckResult(
                name="local_product_smoke",
                status="pass",
                required=True,
                reasonCodes=[],
                redacted=True,
            )
        ],
    )


def test_single_platform_pass_does_not_allow_all_processor_claim() -> None:
    decision = evaluate_platform_claims(
        [_passing_report("darwin-arm64")],
        requested_claim="all processors supported",
    )

    assert decision.status == "blocked"
    assert decision.supported_claims == ["darwin-arm64"]
    assert "OVERBROAD_PLATFORM_CLAIM" in decision.blocking_reasons
    assert "darwin-x64" in decision.not_evidenced_targets
    assert "windows-x64" in decision.not_evidenced_targets
    assert "linux-x64" in decision.not_evidenced_targets


def test_not_evidenced_targets_do_not_fail_product_claim_boundary() -> None:
    decision = evaluate_platform_claims([_passing_report("windows-x64")])

    assert decision.status == "pass"
    assert decision.supported_claims == ["windows-x64"]
    assert "darwin-arm64" in decision.not_evidenced_targets
    assert decision.blocking_reasons == []

