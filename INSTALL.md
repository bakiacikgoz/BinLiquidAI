# Install

## Supported Baseline

- Linux runtime host for primary deployment
- macOS for operator tooling and local verification tasks
- Python 3.11
- `uv` package manager

## Online Install

```bash
make install
uv run binliquid --version
uv run binliquid doctor --profile balanced
```

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
