from __future__ import annotations

import subprocess
from pathlib import Path


def find_matches(
    query: str,
    root_dir: str | Path = ".",
    max_matches: int = 8,
    max_columns: int = 240,
) -> list[dict[str, str | int]]:
    root = Path(root_dir)
    if not query.strip() or not root.exists():
        return []

    cmd = [
        "rg",
        "-n",
        "--no-heading",
        "--color",
        "never",
        "--max-count",
        str(max_matches),
        "--max-columns",
        str(max_columns),
        query,
        str(root),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return []

    if proc.returncode not in (0, 1):
        return []

    results: list[dict[str, str | int]] = []
    for line in proc.stdout.splitlines()[:max_matches]:
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        path, line_no, text = parts
        results.append({"path": path, "line": int(line_no), "text": text.strip()})
    return results
