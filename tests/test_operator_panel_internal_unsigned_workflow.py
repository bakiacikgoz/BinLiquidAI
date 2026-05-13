from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/operator-panel-internal-unsigned-build.yml"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_internal_unsigned_workflow_is_manual_only_and_has_no_release_environment():
    workflow = _workflow()

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "tags:" not in workflow
    assert "environment:" not in workflow


def test_internal_unsigned_workflow_uses_no_signing_secrets():
    workflow = _workflow()

    assert "secrets." not in workflow
    assert "MACOS_SIGNING" not in workflow
    assert "APPLE_NOTARY" not in workflow
    assert "WINDOWS_SIGNING" not in workflow


def test_internal_unsigned_artifacts_are_not_public_release_eligible():
    workflow = _workflow()

    assert "operator-panel-internal-unsigned" in workflow
    assert "internal_unsigned" in workflow
    assert "--no-bundle" in workflow
    assert "no_bundle_debug_binary" in workflow
    assert "release_eligible" in workflow
    assert "public_release_allowed" in workflow
    assert "internal_unsigned_artifact_not_public_release_eligible" in workflow
    assert "internal_unsigned_binary_not_public_release_eligible" in workflow


def test_internal_unsigned_workflow_does_not_upload_signed_release_artifacts():
    workflow = _workflow()

    assert "operator-panel-macos-internal-unsigned-binary-${{ matrix.arch }}" in workflow
    assert "operator-panel-windows-internal-unsigned-binary-x64" in workflow
    assert "operator-panel-windows-signed-release-candidate" not in workflow
    assert "Upload signed release-candidate artifacts" not in workflow
