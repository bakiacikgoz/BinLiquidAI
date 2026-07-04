from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_scripts_are_packaged_for_ci_imports() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    packages = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]

    assert "scripts" in packages
    assert (ROOT / "scripts" / "__init__.py").is_file()


def test_operator_panel_workspace_approves_esbuild_build_scripts() -> None:
    workspace = yaml.safe_load((ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8"))

    assert workspace.get("allowBuilds", {}).get("esbuild") is True
