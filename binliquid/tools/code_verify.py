from __future__ import annotations

import ast
from typing import Any


def verify_python_snippet(code: str) -> dict[str, Any]:
    try:
        ast.parse(code)
        return {
            "ok": True,
            "error": None,
        }
    except SyntaxError as exc:
        return {
            "ok": False,
            "error": {
                "message": str(exc),
                "line": exc.lineno,
                "offset": exc.offset,
            },
        }
