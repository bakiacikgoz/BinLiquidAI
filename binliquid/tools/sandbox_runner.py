from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from binliquid.runtime.allowlist import is_allowed_command


@dataclass(slots=True)
class SandboxResult:
    command: list[str]
    allowed: bool
    exit_code: int
    stdout: str
    stderr: str


class SandboxRunner:
    def __init__(self, *, workdir: str | Path = ".", timeout_s: float = 8.0):
        self.workdir = Path(workdir)
        self.timeout_s = timeout_s

    def run(self, command: list[str]) -> SandboxResult:
        if not is_allowed_command(command):
            return SandboxResult(
                command=command,
                allowed=False,
                exit_code=126,
                stdout="",
                stderr="command is not in allowlist",
            )

        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(self.workdir),
                timeout=self.timeout_s,
            )
            return SandboxResult(
                command=command,
                allowed=True,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
            )
        except FileNotFoundError:
            return SandboxResult(
                command=command,
                allowed=True,
                exit_code=127,
                stdout="",
                stderr="command not found",
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                command=command,
                allowed=True,
                exit_code=124,
                stdout="",
                stderr="command timed out",
            )
