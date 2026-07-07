from __future__ import annotations

from binliquid.assistant_tasking.policy_preview import preview_policy


def test_policy_preview_allow_approval_and_deny() -> None:
    read = preview_policy("read_only")
    write = preview_policy("external_write")
    destructive = preview_policy("destructive")

    assert read.decision == "allow"
    assert read.safe_to_submit is True
    assert write.decision == "require_approval"
    assert write.approval_required is True
    assert destructive.decision == "deny"
    assert destructive.safe_to_submit is False
    assert "ASSISTANT_TASK_DESTRUCTIVE_DENIED" in destructive.blocked_reasons
