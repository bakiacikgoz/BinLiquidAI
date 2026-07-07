# Cross-Platform Local Product Readiness

BinLiquid / AegisOS local product readiness is scoped to an OS and architecture target, not to a single CPU model.

Supported claims are evidence-based. A passing `darwin-arm64` run proves Apple Silicon Mac readiness for that run only; it does not prove Intel Mac, Windows, Linux, or all processors.

## Commands

```bash
uv run python scripts/run_local_product_readiness_gate.py --profile enterprise --json
uv run python scripts/run_local_product_readiness_gate.py --profile enterprise --matrix --json
uv run python scripts/build_local_product_handoff_pack.py --profile enterprise --json
```

## Claim Rules

- `supportedClaims` lists only targets with passing local evidence.
- `notEvidencedTargets` are not product failures and are not supported claims.
- Unsupported targets must remain claim-disabled.
- Broad claims such as `all processors supported` are blocked unless every claimed target has evidence.
- Live computer-use stays disabled unless a separate qualification gate enables it.
- Readiness artifacts must not persist raw prompts, secrets, device serials, MAC addresses, or full environment dumps.

M4 may appear only as an example local validation device for `darwin-arm64`; it is not the product target.

