from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github/workflows"
INTERNAL_UNSIGNED = WORKFLOW_ROOT / "operator-panel-internal-unsigned-build.yml"
CLEAN_SMOKE = WORKFLOW_ROOT / "operator-panel-windows-clean-smoke.yml"
WINDOWS_SMOKE = ROOT / "apps/operator-panel/scripts/windows_installer_smoke.ps1"
MACOS_CODESIGN = ROOT / "apps/operator-panel/scripts/codesign_notarize_macos.sh"

FORMER_BRANDS = (("aegis" + "os").casefold(), ("bin" + "liquid").casefold())


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_workflows_use_no_former_product_identity() -> None:
    violations: list[str] = []
    for path in sorted(WORKFLOW_ROOT.glob("*.y*ml")):
        source = _read(path).casefold()
        if any(token in source for token in FORMER_BRANDS):
            violations.append(path.name)
    assert violations == []


def test_internal_unsigned_stages_the_canonical_binary_on_both_platforms() -> None:
    workflow = _read(INTERNAL_UNSIGNED)
    assert workflow.count("imperaos_operator_panel") == 4
    assert "target/debug/imperaos_operator_panel" in workflow
    assert "target/debug/imperaos_operator_panel.exe" in workflow
    assert '"${STAGE_ROOT}/imperaos_operator_panel"' in workflow
    assert '"$stageRoot/imperaos_operator_panel.exe"' in workflow


def test_installer_smoke_uses_the_canonical_product_everywhere() -> None:
    canonical = "ImperaOS Operator Panel"
    assert f'-ExpectedProductName "{canonical}"' in _read(CLEAN_SMOKE)
    assert f'[string]$ExpectedProductName = "{canonical}"' in _read(WINDOWS_SMOKE)


def test_macos_quarantine_metadata_uses_the_canonical_brand() -> None:
    source = _read(MACOS_CODESIGN)
    assert 'QUARANTINE_TAG="0081;$(date +%s);ImperaOS;"' in source


def test_direct_release_scripts_use_no_former_product_identity() -> None:
    violations: list[str] = []
    for path in (WINDOWS_SMOKE, MACOS_CODESIGN):
        source = _read(path).casefold()
        if any(token in source for token in FORMER_BRANDS):
            violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_brand_gate_is_early_and_fail_closed() -> None:
    workflow = _read(WORKFLOW_ROOT / "ci.yml")
    sync = workflow.index("Sync dependencies")
    gate = workflow.index("ImperaOS brand consistency gate")
    lint = workflow.index("Lint")
    assert sync < gate < lint
    assert "run: make brand-consistency-gate" in workflow

    makefile = _read(ROOT / "Makefile")
    target = makefile.split("brand-consistency-gate:", maxsplit=1)[1].split(
        "\n\n", maxsplit=1
    )[0]
    assert "scripts/run_brand_consistency_gate.py" in target
    assert "--mode enforce" in target
