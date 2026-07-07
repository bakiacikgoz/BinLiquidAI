from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from binliquid.local_product.models import LocalEnvironmentProbe, PlatformTarget


@dataclass(frozen=True)
class CommandResult:
    return_code: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str], int], CommandResult]


def default_command_runner(command: list[str], timeout_seconds: int = 10) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return CommandResult(return_code=127, stdout="", stderr=str(exc))
    return CommandResult(
        return_code=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _run_version(runner: CommandRunner, command: list[str]) -> str | None:
    result = runner(command, 10)
    if result.return_code != 0:
        return None
    output = (result.stdout or result.stderr).strip()
    return output.splitlines()[0] if output else "available"


def _pnpm_mode(
    runner: CommandRunner,
    *,
    local_pnpm_path: str | None,
) -> str:
    corepack = runner(["corepack", "pnpm", "--version"], 10)
    if corepack.return_code == 0:
        return "corepack"
    if local_pnpm_path:
        local = runner([local_pnpm_path, "--version"], 10)
        if local.return_code == 0:
            return "local_bin"
    return "missing"


def _default_local_pnpm_path() -> str | None:
    suffix = ".cmd" if os.name == "nt" else ""
    repo_root = Path(__file__).resolve().parents[2]
    bin_dir = repo_root / "apps" / "operator-panel" / "node_modules" / ".bin"
    for tool_name in ("pnpm", "vitest", "vite", "tsc", "tsx"):
        path = bin_dir / f"{tool_name}{suffix}"
        if path.exists():
            return str(path)
    return None


def collect_environment_probe(
    target: PlatformTarget,
    *,
    command_runner: CommandRunner = default_command_runner,
    local_pnpm_path: str | None = None,
    detected_at: str | None = None,
) -> LocalEnvironmentProbe:
    local_pnpm = local_pnpm_path if local_pnpm_path is not None else _default_local_pnpm_path()
    python_version = _run_version(command_runner, ["python", "--version"]) or "missing"
    uv_available = _run_version(command_runner, ["uv", "--version"]) is not None
    node_version = _run_version(command_runner, ["node", "--version"])
    rustc_version = _run_version(command_runner, ["rustc", "--version"])
    cargo_available = _run_version(command_runner, ["cargo", "--version"]) is not None
    tauri_available = _run_version(command_runner, ["cargo", "tauri", "--version"]) is not None
    return LocalEnvironmentProbe(
        target=target,
        pythonVersion=python_version,
        uvAvailable=uv_available,
        nodeVersion=node_version,
        pnpmMode=_pnpm_mode(command_runner, local_pnpm_path=local_pnpm),
        rustcVersion=rustc_version,
        cargoAvailable=cargo_available,
        tauriCliAvailable=tauri_available,
        webviewStatus="available" if target.os == "windows" else "unknown",
        pathStyle="windows" if target.os == "windows" else "posix",
        newlineMode="unknown",
        detectedAt=detected_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )


def mask_home_path(value: str) -> str:
    home = str(Path.home())
    return value.replace(home, "<home>") if home else value


def resolve_executable(name: str) -> str | None:
    return shutil.which(name)
