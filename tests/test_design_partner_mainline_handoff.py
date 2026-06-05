from __future__ import annotations

from pathlib import Path


def test_mainline_runbook_keeps_no_force_push_boundary() -> None:
    text = Path("docs/MAINLINE_INTEGRATION_RUNBOOK.md").read_text(encoding="utf-8")

    assert "Do not force push `main`" in text
    assert "make mainline-gate" in text


def test_rc_evidence_closure_runbook_states_ready_criteria() -> None:
    text = Path("docs/DESIGN_PARTNER_RC_EVIDENCE_CLOSURE.md").read_text(encoding="utf-8")

    assert "`status=pass`" in text
    assert "`designPartnerRcStatus=ready`" in text
    assert "`public-desktop-installer`" in text
    assert "`live-macos-computer-use`" in text
