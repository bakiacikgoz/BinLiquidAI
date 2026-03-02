from __future__ import annotations

import json
from pathlib import Path

from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig


def test_finalize_run_writes_privacy_safe_audit_artifact(tmp_path: Path) -> None:
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
    runtime = GovernanceRuntime(config=cfg)

    runtime.evaluate_task(
        run_id="run-audit",
        task_type="chat",
        user_input="my email is audit@example.com",
    )
    runtime.evaluate_tool_command(
        run_id="run-audit",
        command=["python", "-c", "print('token=abc123')"],
        workdir=Path("."),
    )

    path = runtime.finalize_run(run_id="run-audit", router_reason_code="RULE_ROUTE")
    assert path is not None
    artifact = json.loads(Path(path).read_text(encoding="utf-8"))

    serialized = json.dumps(artifact, ensure_ascii=False)
    assert "audit@example.com" not in serialized
    assert "token=abc123" not in serialized
    assert "governance_decisions" in serialized
