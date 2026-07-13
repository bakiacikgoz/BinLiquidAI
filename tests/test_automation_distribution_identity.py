from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_PATHS = (
    ROOT / "Makefile",
    *sorted((ROOT / ".github" / "workflows").glob("*.yml")),
    *sorted((ROOT / ".github" / "workflows").glob("*.yaml")),
)
REMOVED_AUTOMATION_REFERENCES = {
    "console CLI": re.compile(r"\buv\s+run\s+binliquid(?=\s|$)"),
    "Python module": re.compile(r"\s-m\s+binliquid(?=\s|$)"),
    "compile target": re.compile(r"\bcompileall\s+binliquid(?=\s|$)"),
    "package directory": re.compile(r"(?<![.\w-])binliquid/"),
}


def test_active_automation_uses_imperaos_distribution_identity() -> None:
    violations: list[str] = []

    for path in AUTOMATION_PATHS:
        source = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), start=1):
            for reference_kind, pattern in REMOVED_AUTOMATION_REFERENCES.items():
                if pattern.search(line):
                    relative_path = path.relative_to(ROOT).as_posix()
                    violations.append(
                        f"{relative_path}:{line_number}: {reference_kind}: {line.strip()}"
                    )

    assert violations == [], "removed distribution automation references:\n" + "\n".join(
        violations
    )
