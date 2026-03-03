from __future__ import annotations

from pathlib import Path

from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig


def _runtime(tmp_path: Path) -> GovernanceRuntime:
    cfg = RuntimeConfig.from_profile("default")
    cfg = cfg.model_copy(
        update={
            "governance": cfg.governance.model_copy(
                update={
                    "approval_store_path": str(tmp_path / "approvals.sqlite3"),
                    "audit_dir": str(tmp_path / "audit"),
                }
            )
        }
    )
    return GovernanceRuntime(config=cfg)


def test_handoff_policy_allows_with_default_rule(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    decision, ticket = runtime.evaluate_handoff(
        run_id="job-1",
        from_role="Intake Agent",
        to_role="Execution Agent",
        payload={"output": "ok"},
    )

    assert decision.action.value == "allow"
    assert decision.reason_code == "RULE_ROUTE"
    assert ticket is None


def test_memory_scope_policy_allows_with_default_rule(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    decision, ticket = runtime.evaluate_memory_write(
        run_id="job-2",
        scope="case",
        producer_role="Execution Agent",
        visibility="team",
    )

    assert decision.action.value == "allow"
    assert decision.reason_code == "RULE_ROUTE"
    assert ticket is None
