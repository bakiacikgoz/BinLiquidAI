from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from binliquid.cli import app


def test_local_product_evidence_cli_collect_export_verify_import_reconcile(tmp_path: Path) -> None:
    runner = CliRunner()
    evidence_root = tmp_path / "evidence"
    bundle = tmp_path / "bundle.zip"
    store = tmp_path / "store"

    collect = runner.invoke(
        app,
        [
            "local-product",
            "evidence",
            "collect",
            "--target",
            "windows-x64",
            "--output-root",
            str(evidence_root),
            "--json",
        ],
    )
    assert collect.exit_code == 0, collect.stdout

    export = runner.invoke(
        app,
        [
            "local-product",
            "evidence",
            "export",
            "--manifest",
            str(evidence_root / "platform_evidence_manifest.json"),
            "--bundle",
            str(bundle),
            "--json",
        ],
    )
    assert export.exit_code == 0, export.stdout

    verify = runner.invoke(
        app,
        ["local-product", "evidence", "verify", "--bundle", str(bundle), "--json"],
    )
    assert verify.exit_code == 0, verify.stdout

    imported = runner.invoke(
        app,
        [
            "local-product",
            "evidence",
            "import",
            "--bundle",
            str(bundle),
            "--store-root",
            str(store),
            "--json",
        ],
    )
    assert imported.exit_code == 0, imported.stdout

    reconcile = runner.invoke(
        app,
        [
            "local-product",
            "evidence",
            "reconcile",
            "--store-root",
            str(store),
            "--json",
        ],
    )
    assert reconcile.exit_code == 0, reconcile.stdout
    assert '"windows-x64"' in reconcile.stdout


def test_local_product_rc_handoff_cli_build_and_verify(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "local-product",
            "rc-handoff",
            "build",
            "--evidence-root",
            str(tmp_path / "missing"),
            "--output-root",
            str(tmp_path / "handoff"),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout

    verify = runner.invoke(
        app,
        [
            "local-product",
            "rc-handoff",
            "verify",
            "--manifest",
            str(tmp_path / "handoff" / "manifest.json"),
            "--json",
        ],
    )
    assert verify.exit_code == 0, verify.stdout
