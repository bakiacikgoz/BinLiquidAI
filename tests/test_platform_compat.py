from __future__ import annotations

import subprocess
from types import SimpleNamespace

from imperaos.runtime import platform as platform_mod
from imperaos.tools.local_search import find_matches


def test_platform_helper_maps_windows(monkeypatch) -> None:
    monkeypatch.setattr(platform_mod._platform, "system", lambda: "Windows")
    monkeypatch.setattr(platform_mod._platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(platform_mod._platform, "release", lambda: "11")

    info = platform_mod.current_platform()

    assert info.label == "windows"
    assert platform_mod.is_windows() is True


def test_safe_allowed_roots_uses_downloads_or_temp(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(platform_mod, "default_download_dir", lambda: tmp_path / "Downloads")
    monkeypatch.setattr(platform_mod, "default_temp_dir", lambda: tmp_path / "Temp")
    config = SimpleNamespace(workspace_root=tmp_path / "workspace")

    roots = platform_mod.safe_allowed_roots(config, tmp_path / "jobs")

    assert (tmp_path / "jobs").resolve() in roots
    assert (tmp_path / "Downloads").resolve() in roots
    assert len({str(root).casefold() for root in roots}) == len(roots)


def test_local_search_falls_back_when_rg_cannot_execute(monkeypatch, tmp_path) -> None:
    sample = tmp_path / "sample.md"
    sample.write_text("Fallback policy and router summary lines", encoding="utf-8")

    def blocked_rg(*args, **kwargs):
        del args, kwargs
        raise PermissionError("rg.exe")

    monkeypatch.setattr(subprocess, "run", blocked_rg)

    matches = find_matches("router summary", tmp_path)

    assert matches == [
        {
            "path": str(sample),
            "line": 1,
            "text": "Fallback policy and router summary lines",
        }
    ]
