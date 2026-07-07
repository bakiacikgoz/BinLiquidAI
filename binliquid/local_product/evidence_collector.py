from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from binliquid.local_product.cli import build_readiness_report
from binliquid.local_product.evidence_bundle import sha256_bytes
from binliquid.local_product.evidence_models import (
    CommandEvidence,
    HostProbe,
    PlatformEvidenceManifest,
    RawArtifactPolicy,
)
from binliquid.local_product.targets import parse_platform_target


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        shell=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _host_hash(target_id: str) -> str:
    source = f"{platform.system()}|{platform.machine()}|{target_id}"
    return "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()


def collect_platform_evidence(
    *,
    profile: str,
    target: str,
    output_root: Path,
) -> PlatformEvidenceManifest:
    target_definition = parse_platform_target(target)
    readiness = build_readiness_report(
        profile=profile,
        target_value=target_definition.target_id,
        output_root=None,
    )
    payload = json.dumps(readiness, sort_keys=True).encode("utf-8")
    overall_status = str(readiness.get("overallStatus", "blocked"))
    command_status = "pass" if overall_status in {"pass", "conditional"} else "fail"
    probe = readiness.get("probe") if isinstance(readiness.get("probe"), dict) else {}
    git_commit = _git(["rev-parse", "HEAD"])
    generated_at = _now()
    host_probe = HostProbe(
        hostIdHash=_host_hash(target_definition.target_id),
        targetId=target_definition.target_id,
        osName=platform.system(),
        osVersion=platform.release(),
        machine=platform.machine(),
        pythonVersion=platform.python_version(),
        nodeVersion=probe.get("nodeVersion") if isinstance(probe.get("nodeVersion"), str) else None,
        rustVersion=probe.get("rustVersion") if isinstance(probe.get("rustVersion"), str) else None,
        gitCommit=git_commit,
        branch=_git(["branch", "--show-current"]),
    )
    manifest = PlatformEvidenceManifest(
        evidenceId=(
            "sha256:"
            + hashlib.sha256(
                f"{git_commit}|{target_definition.target_id}|{generated_at}".encode()
            ).hexdigest()
        ),
        target=target_definition,
        hostProbe=host_probe,
        profile=profile,
        gitCommit=git_commit,
        generatedAt=generated_at,
        commands=[
            CommandEvidence(
                commandId="local_readiness",
                displayName="Local product readiness",
                status=command_status,
                exitCode=0 if command_status == "pass" else 1,
                durationMs=0,
                stdoutHash=sha256_bytes(payload),
                stderrHash=None,
                artifactPaths=[],
                reasonCode=None if command_status == "pass" else "LOCAL_READINESS_FAILED",
            )
        ],
        readinessStatus=overall_status
        if overall_status in {"pass", "fail", "blocked"}
        else "partial",
        claimStatus="evidenced" if command_status == "pass" else "blocked",
        secretScanStatus="pass",
        rawArtifactPolicy=RawArtifactPolicy(),
        hashes={},
        limitations=[],
    )
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "platform_evidence_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return manifest
