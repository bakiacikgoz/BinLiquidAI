from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_model_provider_governance_evidence import generate_evidence
from scripts.run_provider_governance_gate import run_gate


def test_provider_governance_gate_passes_without_live_network() -> None:
    report = run_gate(profile="enterprise")

    assert report["status"] == "pass"
    assert report["remoteProvidersEnabled"] is False
    assert report["checks"]["publicCloudConfidentialDenied"] is True
    assert report["checks"]["redactedEnvelopeSample"] is True


def test_provider_governance_gate_cli_outputs_stable_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_provider_governance_gate.py",
            "--profile",
            "enterprise",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"] == "model_provider.governance_gate/v1"
    assert payload["status"] == "pass"
    assert "sk-" not in result.stdout
    assert "Bearer " not in result.stdout


def test_provider_governance_evidence_pack_writes_required_files(tmp_path: Path) -> None:
    result = generate_evidence(profile="enterprise", output_dir=tmp_path)

    assert result["status"] == "pass"
    expected = {
        "provider-governance-gate.json",
        "provider-registry-snapshot.redacted.json",
        "provider-policy-simulation-public-local.json",
        "provider-policy-simulation-confidential-public-cloud-blocked.json",
        "provider-envelope-sample.redacted.json",
        "provider-ui-snapshot-summary.json",
        "PROVIDER_GOVERNANCE_V1_CLOSURE.md",
    }
    assert expected <= set(result["files"])
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in tmp_path.iterdir() if path.is_file()
    )
    assert "sk-test-secret" not in combined
    assert "user@example.com" not in combined
    assert (tmp_path / "canary").is_dir()
