from __future__ import annotations

import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ICON_ROOT = REPO_ROOT / "apps" / "operator-panel" / "src-tauri" / "icons"

PNG_DIMENSIONS = {
    "32x32.png": (32, 32),
    "128x128.png": (128, 128),
    "128x128@2x.png": (256, 256),
    "icon.png": (512, 512),
    "Square30x30Logo.png": (30, 30),
    "Square44x44Logo.png": (44, 44),
    "Square71x71Logo.png": (71, 71),
    "Square89x89Logo.png": (89, 89),
    "Square107x107Logo.png": (107, 107),
    "Square142x142Logo.png": (142, 142),
    "Square150x150Logo.png": (150, 150),
    "Square284x284Logo.png": (284, 284),
    "Square310x310Logo.png": (310, 310),
    "StoreLogo.png": (50, 50),
}

OBSOLETE_SCREENSHOTS = (
    "ChatGPT Image 17 May 2026 18_43_41 (1).png",
    "ChatGPT Image 17 May 2026 18_43_41 (2).png",
    "ChatGPT Image 17 May 2026 18_43_42 (3).png",
)


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_code_native_imperaos_icon_source_is_tracked_with_established_geometry() -> None:
    source = (ICON_ROOT / "imperaos-source.svg").read_text(encoding="utf-8")

    assert "<title>ImperaOS desktop icon</title>" in source
    assert "M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" in source
    assert "M12 7.5l4 2.3v4.4l-4 2.3-4-2.3V9.8l4-2.3z" in source


def test_generated_tauri_icon_set_has_expected_formats_and_dimensions() -> None:
    for name, expected in PNG_DIMENSIONS.items():
        assert _png_dimensions(ICON_ROOT / name) == expected

    assert (ICON_ROOT / "icon.ico").read_bytes().startswith(b"\x00\x00\x01\x00")
    assert (ICON_ROOT / "icon.icns").read_bytes().startswith(b"icns")


def test_unreferenced_former_identity_screenshots_are_removed() -> None:
    plan_root = REPO_ROOT / "docs" / "plans"

    assert [name for name in OBSOLETE_SCREENSHOTS if (plan_root / name).exists()] == []
