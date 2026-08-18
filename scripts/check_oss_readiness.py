from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "NOTICE",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SUPPORT.md",
    "CHANGELOG.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/CODEOWNERS",
)


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing required OSS file: {relative}")

    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.is_file():
        errors.append("missing required package metadata: pyproject.toml")
    else:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project", {})
        if project.get("name") != "imperaos":
            errors.append("pyproject project.name must be 'imperaos'")
        if project.get("license") != "Apache-2.0":
            errors.append("pyproject project.license must be 'Apache-2.0'")

        scripts = project.get("scripts", {})
        if "imperaos" not in scripts:
            errors.append("pyproject must expose the 'imperaos' CLI")
        if "binliquid" not in scripts:
            errors.append("pyproject must retain the 'binliquid' compatibility CLI")

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        for marker in ("Why ImperaOS", "CONTRIBUTING.md", "SECURITY.md", "Apache-2.0"):
            if marker not in readme:
                errors.append(f"README is missing required public marker: {marker}")

    return errors


def main() -> int:
    errors = check_repository(Path("."))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OSS readiness checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
