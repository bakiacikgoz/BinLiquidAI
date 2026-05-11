from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_preflights_windows_credentials_before_build():
    workflow = (ROOT / ".github/workflows/operator-panel-release-windows.yml").read_text(
        encoding="utf-8"
    )

    preflight = workflow.index("Validate Windows signing credentials")
    checkout = workflow.index("Checkout")
    runtime_build = workflow.index("Build bundled runtime")
    nsis_build = workflow.index("Build unsigned NSIS artifact")

    assert preflight < checkout
    assert preflight < runtime_build
    assert preflight < nsis_build


def test_release_workflow_uploads_blocked_windows_preflight_evidence():
    workflow = (ROOT / ".github/workflows/operator-panel-release-windows.yml").read_text(
        encoding="utf-8"
    )

    assert "windows-release-credential-preflight/v1" in workflow
    assert "blocked_external_credentials" in workflow
    assert "operator-panel-windows-credential-preflight" in workflow
    assert "secret_material_written" in workflow
    assert "WINDOWS_SIGNING_CERT_PFX_B64" in workflow
    assert "WINDOWS_SIGNING_CERT_PASSWORD" in workflow


def test_release_workflow_does_not_grant_public_release_in_signing_step():
    workflow = (ROOT / ".github/workflows/operator-panel-release-windows.yml").read_text(
        encoding="utf-8"
    )

    assert "public_release_allowed" not in workflow


def test_release_workflow_runs_public_gate_evaluator():
    workflow = (ROOT / ".github/workflows/operator-panel-release-windows.yml").read_text(
        encoding="utf-8"
    )

    assert "scripts/evaluate_windows_release_gate.py" in workflow
    assert "windows-public-release-gate.json" in workflow


def test_promote_workflow_uses_fail_on_blocked():
    workflow = (ROOT / ".github/workflows/operator-panel-promote-windows.yml").read_text(
        encoding="utf-8"
    )

    assert "--fail-on-blocked" in workflow
    assert "promote-windows" in workflow


def test_clean_smoke_workflow_never_allows_unsigned_smoke():
    workflow = (ROOT / ".github/workflows/operator-panel-windows-clean-smoke.yml").read_text(
        encoding="utf-8"
    )

    assert "-AllowUnsignedSmoke" not in workflow
    assert "-RunInstall" in workflow
    assert "-CleanVm" in workflow
    assert "clean-smoke-windows" in workflow
