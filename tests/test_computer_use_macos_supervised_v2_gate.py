from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_macos_supervised_vision_gate.py"
FIXTURE_ROOT = REPO_ROOT / "contracts" / "computer_use" / "fixtures"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location(
        "evaluate_macos_supervised_vision_gate",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _write_evidence(root: Path, fixture: dict[str, object]) -> None:
    files = fixture.get("files", {})
    assert isinstance(files, dict)
    root.mkdir(parents=True, exist_ok=True)
    for filename, payload in files.items():
        (root / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def test_gate_blocks_safely_on_non_macos_without_evidence(tmp_path: Path) -> None:
    module = _load_gate_module()
    fixture = _load_fixture("macos_supervised_v2_gate_blocked_fixture.json")

    report = module.evaluate_macos_supervised_v2_gate(
        evidence_root=tmp_path,
        current_platform=str(fixture["current_platform"]),
    )

    assert report["status"] == fixture["expected"]["status"]
    assert report["public_live_claim_allowed"] is False
    assert fixture["expected"]["blocking_reason"] in report["blocking_reasons"]
    assert report["evidence"]["provider_doctor_present"] is False
    assert report["safety"]["raw_screenshot_count"] == 0


def test_gate_passes_with_complete_macos_fixture(tmp_path: Path) -> None:
    module = _load_gate_module()
    fixture = _load_fixture("macos_supervised_v2_gate_pass_fixture.json")
    _write_evidence(tmp_path, fixture)

    report = module.evaluate_macos_supervised_v2_gate(
        evidence_root=tmp_path,
        current_platform=str(fixture["current_platform"]),
    )

    assert report["status"] == fixture["expected"]["status"]
    assert report["blocking_reasons"] == []
    assert report["public_live_claim_allowed"] is False
    assert all(report["evidence"].values())
    assert report["safety"]["raw_screenshot_persistence"] is False
    assert report["safety"]["raw_screenshot_count"] == 0
    assert report["safety"]["sensitive_surface_stop_verified"] is True
    assert report["safety"]["approval_freshness_verified"] is True
    assert report["safety"]["semantic_verifier_verified"] is True
    assert report["safety"]["replay_integrity_verified"] is True


def test_gate_fails_when_raw_screenshot_evidence_is_positive(tmp_path: Path) -> None:
    module = _load_gate_module()
    fixture = _load_fixture("macos_supervised_v2_gate_fail_raw_screenshot_fixture.json")
    _write_evidence(tmp_path, fixture)

    report = module.evaluate_macos_supervised_v2_gate(
        evidence_root=tmp_path,
        current_platform=str(fixture["current_platform"]),
    )

    assert report["status"] == fixture["expected"]["status"]
    assert fixture["expected"]["blocking_reason"] in report["blocking_reasons"]
    assert report["public_live_claim_allowed"] is False
    assert report["safety"]["raw_screenshot_count"] == fixture["expected"][
        "raw_screenshot_count"
    ]


def test_gate_script_writes_json_and_markdown(tmp_path: Path) -> None:
    module = _load_gate_module()
    fixture = _load_fixture("macos_supervised_v2_gate_pass_fixture.json")
    evidence_root = tmp_path / "evidence"
    _write_evidence(evidence_root, fixture)
    output = tmp_path / "macos_supervised_v2_gate.json"
    markdown = tmp_path / "MACOS_SUPERVISED_V2_GATE.md"

    exit_code = module.main(
        [
            "--evidence-root",
            str(evidence_root),
            "--output",
            str(output),
            "--markdown",
            str(markdown),
            "--current-platform",
            "macos",
            "--json",
        ]
    )

    assert exit_code == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["status"] == "pass"
    assert markdown.read_text(encoding="utf-8").startswith("# macOS Supervised Vision v2 Gate")
