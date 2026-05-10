from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_macos_release_workflow_preflights_credentials_before_build():
    workflow = (ROOT / ".github/workflows/operator-panel-release-macos.yml").read_text(
        encoding="utf-8"
    )

    preflight = workflow.index("Validate signing and notarization credentials")
    checkout = workflow.index("Checkout")
    runtime_build = workflow.index("Build bundled runtime")
    tauri_build = workflow.index("Build Tauri bundle")

    assert preflight < checkout
    assert preflight < runtime_build
    assert preflight < tauri_build


def test_macos_release_workflow_uploads_blocked_preflight_evidence():
    workflow = (ROOT / ".github/workflows/operator-panel-release-macos.yml").read_text(
        encoding="utf-8"
    )

    assert "macos-release-credential-preflight/v1" in workflow
    assert "blocked_external_credentials" in workflow
    assert "operator-panel-macos-credential-preflight-${{ matrix.arch }}" in workflow
    assert "secret_material_written" in workflow
    assert "MACOS_SIGNING_IDENTITY" in workflow
    assert "APPLE_NOTARY_KEY_P8_B64" in workflow


def test_macos_release_workflow_does_not_grant_public_release_permission():
    workflow = (ROOT / ".github/workflows/operator-panel-release-macos.yml").read_text(
        encoding="utf-8"
    )

    assert "public_release_allowed" not in workflow
