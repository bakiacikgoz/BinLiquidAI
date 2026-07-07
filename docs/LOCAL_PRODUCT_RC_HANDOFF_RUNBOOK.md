# Local Product RC Handoff Runbook

The RC handoff pack is the release-review surface for local product platform
claims. It summarizes imported evidence, product-complete closure status,
supported claims, blocked claims, and hash-checked handoff artifacts.

## Build

```bash
uv run binliquid local-product rc-handoff build --profile enterprise --json
```

The default output is `artifacts/local-product-rc-handoff/`:

- `manifest.json`
- `platform_evidence_reconciliation.json`
- `LOCAL_PRODUCT_RC_HANDOFF.md`
- `PRODUCT_COMPLETE_PR_BODY.md`

## Verify

```bash
uv run binliquid local-product rc-handoff verify \
  --manifest artifacts/local-product-rc-handoff/manifest.json \
  --json
```

The verification checks every file listed in `hashLedger`.

## Status Semantics

- `ready`: platform reconciliation passes and product-complete closure passed.
- `conditional`: platform reconciliation passes but product-complete closure has
  not been generated in the workspace.
- `blocked`: reconciliation or product-complete closure has a release blocker.

## Release Review Checklist

1. Run `platform-evidence-orchestrator-gate`.
2. Run `product-complete-closure-gate`.
3. Build the RC handoff pack.
4. Verify the handoff manifest.
5. Confirm `supportedClaims` contains only targets with imported evidence.
6. Confirm `blockedClaims` and `noShipBlockers` are empty before any RC-ready
   statement.
