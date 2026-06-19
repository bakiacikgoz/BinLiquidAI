from __future__ import annotations

import json
from pathlib import Path

from scripts.run_enterprise_workspace_release_closure_gate import (
    parse_pytest_failures,
    render_markdown,
    render_pr_body,
    run_closure_gate,
)


def test_parse_pytest_failures_extracts_node_ids() -> None:
    failures = parse_pytest_failures(
        [
            "FAILED tests/test_example.py::test_one - AssertionError",
            "FAILED tests/test_other.py::TestThing::test_two - RuntimeError",
        ]
    )

    assert failures == [
        "tests/test_example.py::test_one",
        "tests/test_other.py::TestThing::test_two",
    ]


def test_release_closure_gate_writes_reports_without_commands(tmp_path: Path) -> None:
    report = run_closure_gate(
        profile="enterprise",
        output_root=tmp_path,
        pytest_mode="skip",
        skip_commands=True,
    )

    assert report["schemaVersion"] == "enterprise-workspace.release-closure/v1"
    assert report["status"] == "pass"
    assert report["pushPerformed"] is False
    assert (tmp_path / "closure_report.json").exists()
    assert (tmp_path / "closure_report.md").exists()
    assert (tmp_path / "pr_body.md").exists()
    assert json.loads((tmp_path / "closure_report.json").read_text(encoding="utf-8"))["status"]


def test_release_closure_markdown_and_pr_body_are_redacted(tmp_path: Path) -> None:
    report = run_closure_gate(
        profile="enterprise",
        output_root=tmp_path,
        pytest_mode="skip",
        skip_commands=True,
    )
    markdown = render_markdown(report)
    pr_body = render_pr_body(report)

    assert "Enterprise Workspace Release Closure" in markdown
    assert "## Summary" in pr_body
    assert "shown-once-token-test-value" not in markdown
    assert "shown-once-token-test-value" not in pr_body
