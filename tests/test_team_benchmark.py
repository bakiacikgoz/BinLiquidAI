from __future__ import annotations

import json
from pathlib import Path

from benchmarks.run_team import run_team_benchmark


def test_team_benchmark_supports_deterministic_mock(tmp_path: Path) -> None:
    spec_path = tmp_path / "team.json"
    spec_payload = {
        "version": "1",
        "team": {
            "team_id": "bench-team",
            "supervisor_policy": "sequential_then_parallel",
            "agents": [
                {
                    "agent_id": "agent-intake",
                    "role": "Intake Agent",
                    "allowed_task_types": ["chat", "plan"],
                    "profile_name": "lite",
                    "model_overrides": {},
                    "memory_scope_access": ["session", "case"],
                    "tool_policy_profile": "default",
                    "approval_mode": "auto",
                }
            ],
            "handoff_rules": [],
            "termination_rules": {
                "max_tasks": 8,
                "max_retries": 1,
                "max_handoff_depth": 8,
            },
        },
        "tasks": [],
    }
    spec_path.write_text(json.dumps(spec_payload, ensure_ascii=False), encoding="utf-8")
    output_path = tmp_path / "team_bench.json"

    payload = run_team_benchmark(
        profile="lite",
        suite="smoke",
        spec_path=str(spec_path),
        task_limit=1,
        output_path=str(output_path),
        deterministic_mock=True,
    )

    assert payload["execution_mode"] == "deterministic_mock"
    assert payload["task_count"] == 1
    assert output_path.exists()
