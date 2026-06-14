from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from binliquid.control_plane.field_evidence import (
    collect_field_evidence_bundle,
    prepare_field_evidence_session,
    validate_independent_operator_attestation,
)
from binliquid.runtime.config import RuntimeConfig


def test_operator_attestation_rejects_placeholder_operator(tmp_path: Path) -> None:
    session, bundle, attestation_path = _field_fixture(tmp_path)
    payload = json.loads(attestation_path.read_text(encoding="utf-8"))
    payload["operatorDisplayName"] = "TODO operator"
    attestation_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = validate_independent_operator_attestation(
        attestation_path=attestation_path,
        session=session,
        bundle=bundle,
    )

    assert result.status == "invalid"
    assert result.blocking_reasons[0].startswith("OPERATOR_ATTESTATION_INVALID")


def test_operator_attestation_rejects_bundle_mismatch(tmp_path: Path) -> None:
    session, bundle, attestation_path = _field_fixture(tmp_path)
    payload = json.loads(attestation_path.read_text(encoding="utf-8"))
    payload["bundleSha256"] = "sha256:wrong"
    attestation_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    result = validate_independent_operator_attestation(
        attestation_path=attestation_path,
        session=session,
        bundle=bundle,
    )

    assert result.status == "invalid"
    assert "ATTESTATION_BUNDLE_HASH_MISMATCH" in result.blocking_reasons


def _field_fixture(tmp_path: Path):
    evidence_root = tmp_path / "artifacts"
    evidence_root.mkdir()
    (evidence_root / "security_posture.json").write_text('{"status":"pass"}\n', encoding="utf-8")
    (evidence_root / "support_bundle_manifest.json").write_text(
        '{"status":"ready"}\n', encoding="utf-8"
    )
    field_root = evidence_root / "design-partner-field-evidence"
    session = prepare_field_evidence_session(
        config=RuntimeConfig.from_profile("enterprise"),
        mode="target_environment",
        environment_label="Partner QA Workstation",
        output_root=field_root,
        force_new_session=True,
    )
    bundle = collect_field_evidence_bundle(
        session=session,
        evidence_root=evidence_root,
        output_root=field_root,
    )
    attestation_path = field_root / "operator_attestation.json"
    attestation_path.write_text(
        json.dumps(
            {
                "schemaVersion": "binliquid-non-developer-operator-attestation/v1",
                "sessionId": session.session_id,
                "releasePackId": "design-partner-rc-v1",
                "targetEnvironmentLabelHash": session.target_environment.environment_label_hash,
                "bundleSha256": bundle.bundle_sha256,
                "operatorDisplayName": "Field Operator One",
                "operatorRole": "Design Partner Operations Reviewer",
                "nonDeveloperOperator": True,
                "reviewedRunbook": True,
                "completedValidation": True,
                "signedAtUtc": datetime.now(UTC).isoformat(),
                "notesRedacted": "Reviewed hash-only field pack.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return session, bundle, attestation_path
