# Local Product Handoff Runbook

## Windows x64

```powershell
uv run python scripts/run_local_product_readiness_gate.py --profile enterprise --target windows-x64 --json
make local-product-ready-windows
```

## macOS Apple Silicon

```bash
uv run python scripts/run_local_product_readiness_gate.py --profile enterprise --target darwin-arm64 --json
make local-product-ready-macos
```

## macOS Intel

```bash
uv run python scripts/run_local_product_readiness_gate.py --profile enterprise --target darwin-x64 --json
```

## Linux x64

```bash
uv run python scripts/run_local_product_readiness_gate.py --profile enterprise --target linux-x64 --json
make local-product-ready-linux
```

## Handoff Pack

```bash
uv run python scripts/build_local_product_handoff_pack.py --profile enterprise --json
```

Review `supportedClaims` before making any release statement. `notEvidencedTargets` means no claim has been made for that target yet.

