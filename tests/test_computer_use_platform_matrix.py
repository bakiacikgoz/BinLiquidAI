from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from binliquid.computer_use.vision_runtime.platforms import evaluate_platform_matrix
from binliquid.runtime.config import ComputerUseRuntimeConfig

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "evaluate_computer_use_platform_matrix.py"


def test_platform_matrix_passes_when_all_platforms_are_fail_closed() -> None:
    matrix = evaluate_platform_matrix(ComputerUseRuntimeConfig(), current_platform="windows")

    assert matrix["status"] == "pass"
    assert matrix["liveAutomationDefault"] is False
    assert matrix["rawScreenshotPersistenceDefault"] is False
    assert matrix["platforms"]["windows"]["reasonCode"] == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    assert matrix["platforms"]["linux"]["reasonCode"] == "LINUX_COMPUTER_USE_NOT_QUALIFIED"
    assert matrix["securityInvariants"]["screenTextTreatedAsUntrusted"] is True
    assert matrix["blockers"] == []


def test_platform_matrix_fails_if_live_claim_has_no_valid_evidence() -> None:
    config = ComputerUseRuntimeConfig(
        vision_enabled=True,
        vision_provider="mock",
        windows_live_enabled=True,
        windows_capture_backend="mock",
        windows_input_backend="mock",
    )
    matrix = evaluate_platform_matrix(config, current_platform="windows")

    assert matrix["status"] == "fail"
    assert "windows_live_ready_without_valid_qualification" in matrix["blockers"]


def test_platform_matrix_script_writes_json_and_markdown(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "evaluate_computer_use_platform_matrix",
        SCRIPT_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    output = tmp_path / "matrix.json"
    markdown = tmp_path / "matrix.md"
    exit_code = module.main(
        [
            "--profile",
            "balanced",
            "--output",
            str(output),
            "--markdown",
            str(markdown),
        ]
    )

    assert exit_code == 0
    assert output.exists()
    assert markdown.exists()
