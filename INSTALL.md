# Install

## Supported Baseline

- Linux runtime host for primary deployment
- macOS for operator tooling and local verification tasks
- Windows x64 for core CLI, operator panel, bundled runtime, and installer smoke
- Python 3.11
- `uv` package manager

## Online Install

```bash
make install
uv run binliquid --version
uv run binliquid doctor --profile balanced
```

## Windows Online Install

```powershell
winget install --id=astral-sh.uv -e
uv sync --python 3.11 --extra dev
uv run python -m binliquid --version
uv run python -m binliquid doctor --profile balanced --json
uv run python -m binliquid operator capabilities --json
```

Alternative uv installer:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Windows support currently covers core CLI and operator-panel packaging. Windows
live computer-use automation remains disabled unless a Windows qualification
report explicitly enables it.

## Enterprise Fixture Preparation

For local enterprise validation, prepare signing keys and a verified identity assertion:

```bash
uv run python scripts/prepare_enterprise_fixture.py --root .
```

## Offline Install

Expected offline bundle contents:

- pinned wheelhouse or dependency cache
- application source or built artifact
- config templates
- policy bundle manifest
- key bootstrap instructions

## Enterprise Validation After Install

```bash
uv run binliquid security baseline --profile enterprise --json
uv run binliquid auth whoami --profile enterprise --json
uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json
```
