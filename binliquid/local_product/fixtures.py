from __future__ import annotations

from binliquid.local_product.claim_guard import evaluate_platform_claims
from binliquid.local_product.models import GateCheckResult
from binliquid.local_product.platforms import parse_target
from binliquid.local_product.probe import CommandResult, collect_environment_probe
from binliquid.local_product.readiness import evaluate_local_product_readiness


def _runner(command: list[str], timeout_seconds: int = 10) -> CommandResult:
    del timeout_seconds
    versions = {
        "python": "Python 3.11.9",
        "uv": "uv 0.7.0",
        "node": "v22.12.0",
        "corepack": "9.15.0",
        "rustc": "rustc 1.88.0",
        "cargo": "cargo 1.88.0",
    }
    return CommandResult(0, versions.get(command[0], "ok"), "")


def _report(target_id: str, *, status: str = "pass"):
    target = parse_target(target_id)
    probe = collect_environment_probe(
        target,
        command_runner=_runner,
        detected_at="2026-07-07T00:00:00Z",
    )
    check_status = "pass" if status == "pass" else "not_applicable"
    return evaluate_local_product_readiness(
        profile="enterprise",
        target=target,
        probe=probe,
        checks=[
            GateCheckResult(
                name="fixture",
                status=check_status,
                required=status == "pass",
                reasonCodes=[] if status == "pass" else ["TARGET_NOT_EVIDENCED"],
                redacted=True,
            )
        ],
    )


def contract_fixtures() -> dict[str, dict[str, object]]:
    windows = _report("windows-x64")
    darwin = _report("darwin-arm64")
    decision = evaluate_platform_claims([darwin], requested_claim="all processors supported")
    unsupported = parse_target("linux-riscv64")
    return {
        "windows_x64_pass.json": {
            "fixtureSchema": "local_product_readiness_report",
            "expectedStatus": "pass",
            "payload": windows.model_dump(mode="json", by_alias=True),
        },
        "darwin_arm64_pass.json": {
            "fixtureSchema": "local_product_readiness_report",
            "expectedStatus": "pass",
            "payload": darwin.model_dump(mode="json", by_alias=True),
        },
        "darwin_x64_not_evidenced.json": {
            "fixtureSchema": "platform_target",
            "expectedStatus": "not_evidenced",
            "payload": parse_target("darwin-x64").model_dump(mode="json", by_alias=True),
        },
        "linux_x64_pass.json": {
            "fixtureSchema": "local_product_readiness_report",
            "expectedStatus": "pass",
            "payload": _report("linux-x64").model_dump(mode="json", by_alias=True),
        },
        "unsupported_arch_blocked.json": {
            "fixtureSchema": "platform_target",
            "expectedStatus": "blocked",
            "payload": unsupported.model_dump(mode="json", by_alias=True),
        },
        "m4_overclaim_rejected.json": {
            "fixtureSchema": "local_product_claim_boundary",
            "expectedStatus": "blocked",
            "payload": {
                "schemaVersion": decision.schema_version,
                "targetId": "darwin-arm64",
                "claimAllowed": False,
                "supportedClaims": decision.supported_claims,
                "notEvidencedTargets": decision.not_evidenced_targets,
                "unsupportedTargets": decision.unsupported_targets,
                "blockedTargets": decision.blocked_targets,
                "productClaimSummary": decision.product_claim_summary,
                "blockingReasons": decision.blocking_reasons,
            },
        },
        "raw_secret_leak_fail.json": {
            "fixtureSchema": "local_product_readiness_report",
            "expectedStatus": "fail",
            "payload": windows.model_copy(
                update={"secret_scan_status": "fail", "no_ship_blockers": ["SECRET_LEAK_DETECTED"]}
            ).model_dump(mode="json", by_alias=True),
        },
    }

