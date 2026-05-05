from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = REPO_ROOT / "scripts" / "evaluate_computer_use_integration_gate.py"


def _load_gate() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "evaluate_computer_use_integration_gate",
        GATE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_computer_use_integration_gate_current_path_is_merge_ready() -> None:
    gate = _load_gate()
    report = gate.evaluate_integration_gate(
        repo=REPO_ROOT,
        profile="balanced",
        path_check_mode="current-only",
    )

    assert report["status"] == "pass"
    assert report["merge_ready"] is True
    assert report["checks"]["console_entrypoints"] is True
    assert report["checks"]["operator_contract"] is True
    assert report["checks"]["security_invariants"] is True
    assert report["defaults"]["checks"]["vision_enabled"]["value"] is False
    assert report["defaults"]["checks"]["raw_screenshot_max_count"]["value"] == 0
    assert report["release_status"]["public_live_claims"] == "blocked"
    assert "live_macos_qualification_missing" in report["release_status"]["live_blockers"]
    assert report["platform_gates"]["live_macos_qualification_blocks_foundation_merge"] is False


def test_computer_use_integration_gate_markdown_contains_stop_go_fields() -> None:
    gate = _load_gate()
    report = gate.evaluate_integration_gate(
        repo=REPO_ROOT,
        profile="balanced",
        path_check_mode="current-only",
    )
    markdown = gate.render_markdown(report)

    assert "# Computer-Use Integration Gate" in markdown
    assert "Merge ready" in markdown
    assert "Public live claims" in markdown
    assert "live_macos_qualification_missing" in markdown
