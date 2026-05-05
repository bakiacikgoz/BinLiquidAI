from __future__ import annotations

import json
import os
import subprocess
import tomllib
from pathlib import Path

from binliquid import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]


def _entrypoint_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("BINLIQUID_")}
    env.pop("VIRTUAL_ENV", None)
    env["NO_COLOR"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["UV_LINK_MODE"] = "copy"
    return env


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=_entrypoint_env(),
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_editable_console_scripts_use_path_safe_exact_mode() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    dependencies = set(pyproject["project"]["dependencies"])

    assert wheel["dev-mode-exact"] is True
    assert set(wheel["packages"]) >= {"binliquid", "benchmarks", "research"}
    assert "editables>=0.3,<1.0" in dependencies


def test_console_and_module_entrypoints_work_from_current_unicode_path() -> None:
    version_commands = [
        ["uv", "run", "binliquid", "--version"],
        ["uv", "run", "python", "-m", "binliquid", "--version"],
    ]
    for command in version_commands:
        result = _run(command)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == __version__

    capability_commands = [
        ["uv", "run", "binliquid", "operator", "capabilities", "--json"],
        ["uv", "run", "python", "-m", "binliquid", "operator", "capabilities", "--json"],
    ]
    for command in capability_commands:
        result = _run(command)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["contractVersion"] == "2.0"
        assert payload["features"]["computerUseVisionRuntime"]["enabled"] is False
