from __future__ import annotations

import subprocess
import sys

from binliquid import __version__


def test_python_module_entrypoint_supports_version_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "binliquid", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == __version__
