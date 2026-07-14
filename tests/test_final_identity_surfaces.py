from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def _former(*parts: str) -> str:
    return "".join(parts)


def _tracked_paths() -> list[Path]:
    assert GIT is not None, "git is required for the final identity test"
    result = subprocess.run(
        [GIT, "-C", str(REPO_ROOT), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [REPO_ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def test_tracked_text_and_paths_do_not_publish_former_product_families() -> None:
    forbidden = (_former("bin", "liquid"), _former("ae", "gis"))
    findings: list[str] = []

    for path in _tracked_paths():
        relative = path.relative_to(REPO_ROOT).as_posix()
        normalized_path = relative.casefold()
        for token in forbidden:
            if token in normalized_path:
                findings.append(f"path:{relative}:{token}")

        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        normalized_text = text.casefold()
        for token in forbidden:
            if token in normalized_text:
                findings.append(f"content:{relative}:{token}")

    assert findings == []


def test_canonical_state_directory_is_the_only_product_state_ignore() -> None:
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    former_state_root = f".{_former('bin', 'liquid')}/"

    assert ".imperaos/" in ignored
    assert former_state_root not in ignored
