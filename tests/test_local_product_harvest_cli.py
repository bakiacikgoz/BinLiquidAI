from __future__ import annotations

from typer.testing import CliRunner

from binliquid.cli import app


def test_local_product_ci_discover_auth_missing_json(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("binliquid.local_product.github_actions.shutil.which", lambda _: None)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "local-product",
            "ci",
            "discover",
            "--branch",
            "codex/test",
            "--head-sha",
            "a" * 40,
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert "blocked_external_auth" in result.stdout


def test_local_product_source_install_claim_cli_json(tmp_path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "local-product",
            "source-install",
            "claim",
            "--expected-head",
            "a" * 40,
            "--evidence-root",
            str(tmp_path / "missing"),
            "--output-root",
            str(tmp_path / "claim"),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"schemaVersion": "source_install_rc_claim/v1"' in result.stdout
