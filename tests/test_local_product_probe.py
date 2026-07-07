from __future__ import annotations

from binliquid.local_product.platforms import parse_target
from binliquid.local_product.probe import CommandResult, collect_environment_probe


def test_collect_environment_probe_handles_missing_commands_without_crashing() -> None:
    commands: list[tuple[str, ...]] = []

    def runner(command: list[str], timeout_seconds: int = 10) -> CommandResult:
        commands.append(tuple(command))
        executable = command[0].lower()
        if executable == "python":
            return CommandResult(return_code=0, stdout="Python 3.11.9", stderr="")
        return CommandResult(return_code=127, stdout="", stderr="missing")

    probe = collect_environment_probe(
        parse_target("windows-x64"),
        command_runner=runner,
        detected_at="2026-07-07T00:00:00Z",
    )

    assert ("python", "--version") in commands
    assert probe.python_version == "Python 3.11.9"
    assert probe.uv_available is False
    assert probe.node_version is None
    assert probe.pnpm_mode == "missing"
    assert probe.rustc_version is None
    assert probe.path_style == "windows"


def test_collect_environment_probe_prefers_repo_local_pnpm_fallback() -> None:
    def runner(command: list[str], timeout_seconds: int = 10) -> CommandResult:
        if command[:2] == ["corepack", "pnpm"]:
            return CommandResult(return_code=1, stdout="", stderr="shim broken")
        if "pnpm" in command[0]:
            return CommandResult(return_code=0, stdout="9.15.0", stderr="")
        return CommandResult(return_code=0, stdout="ok", stderr="")

    probe = collect_environment_probe(
        parse_target("windows-x64"),
        command_runner=runner,
        local_pnpm_path="apps/operator-panel/node_modules/.bin/pnpm.cmd",
        detected_at="2026-07-07T00:00:00Z",
    )

    assert probe.pnpm_mode == "local_bin"

