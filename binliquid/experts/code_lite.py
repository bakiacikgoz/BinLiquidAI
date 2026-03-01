from __future__ import annotations

import time

from binliquid.experts.base import ExpertBase
from binliquid.schemas.models import ExpertRequest, ExpertResult, ExpertStatus
from binliquid.tools.code_verify import verify_python_snippet


class CodeLiteExpert(ExpertBase):
    name = "code_expert"

    def run(self, request: ExpertRequest) -> ExpertResult:
        started = time.perf_counter()
        lower = request.user_input.lower()

        strategy = "minimal_patch"
        issue_type = "generic"
        snippet = "# Provide minimal code fix based on the request"

        if "python" in lower and "unique" in lower and "sort" in lower:
            issue_type = "algorithm"
            snippet = (
                "def unique_sorted(items):\n"
                "    # Stable and deterministic output\n"
                "    return sorted(set(items))"
            )
        elif "test" in lower and "fail" in lower:
            issue_type = "test_failure"
            strategy = "test_first_fix"
            snippet = (
                "# 1) Reproduce failing test\n"
                "# 2) Apply minimal fix\n"
                "# 3) Re-run focused test suite"
            )
        elif "refactor" in lower:
            issue_type = "refactor"
            strategy = "safe_refactor"
            snippet = (
                "# Refactor plan\n"
                "# - Preserve behavior\n"
                "# - Extract small pure functions\n"
                "# - Add regression tests"
            )

        payload = {
            "issue_type": issue_type,
            "strategy": strategy,
            "candidate_snippet": snippet,
            "notes": "Code expert produced a constrained, verifiable suggestion.",
        }
        if "def " in snippet:
            payload["verification"] = verify_python_snippet(snippet)
        else:
            payload["verification"] = {"ok": True, "error": None}

        elapsed = int((time.perf_counter() - started) * 1000)
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=0.8 if payload["verification"]["ok"] else 0.6,
            payload=payload,
            elapsed_ms=elapsed,
        )
