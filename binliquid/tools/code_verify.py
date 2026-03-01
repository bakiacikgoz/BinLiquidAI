from __future__ import annotations

import ast
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from binliquid.tools.sandbox_runner import SandboxRunner


def verify_python_snippet(
    code: str,
    *,
    workdir: str | Path = ".",
    run_lint: bool = True,
    run_tests: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "parse_ok": False,
        "lint_ok": None,
        "tests_ok": None,
        "details": {},
    }

    try:
        ast.parse(code)
        result["parse_ok"] = True
    except SyntaxError as exc:
        result["details"]["parse_error"] = {
            "message": str(exc),
            "line": exc.lineno,
            "offset": exc.offset,
        }
        return result

    runner = SandboxRunner(workdir=workdir, timeout_s=15)

    # Use an ephemeral file for syntax/lint checks and avoid mutating the repo.
    with NamedTemporaryFile("w", suffix=".py", delete=True) as tmp:
        tmp.write(code)
        tmp.flush()
        py_compile = runner.run(["python", "-m", "py_compile", tmp.name])
        result["details"]["py_compile_exit_code"] = py_compile.exit_code
        if py_compile.exit_code != 0:
            result["lint_ok"] = False
            result["details"]["py_compile_stderr"] = py_compile.stderr.strip()
            return result

        if run_lint:
            lint_run = runner.run(["ruff", "check", "--select", "E,F", "--quiet", tmp.name])
            # ruff not installed should not fail the full verification; keep explicit detail.
            if lint_run.exit_code == 127:
                result["lint_ok"] = None
                result["details"]["lint_skipped"] = "ruff not found"
            else:
                result["lint_ok"] = lint_run.exit_code == 0
                result["details"]["lint_exit_code"] = lint_run.exit_code
                if lint_run.exit_code != 0:
                    result["details"]["lint_stderr"] = lint_run.stderr.strip()
        else:
            result["lint_ok"] = None

    if run_tests:
        test_run = runner.run(["uv", "run", "pytest", "--collect-only", "-q"])
        if test_run.exit_code == 127:
            result["tests_ok"] = None
            result["details"]["tests_skipped"] = "uv not found"
        else:
            # collect-only can return non-zero on repo test issues; keep signal explicit.
            result["tests_ok"] = test_run.exit_code == 0
            result["details"]["tests_exit_code"] = test_run.exit_code
            if test_run.exit_code != 0:
                result["details"]["tests_stderr"] = test_run.stderr.strip()
    return result
