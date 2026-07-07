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
- `source_install_rc_claim.json`
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

- `ready`: platform reconciliation, source install RC claim, and
  product-complete closure passed.
- `conditional`: platform reconciliation passes but product-complete closure has
  not been generated in the workspace.
- `blocked`: reconciliation, source install claim, or product-complete closure
  has a release blocker.

## Release Review Checklist

1. Run `remote-platform-evidence-harvest-gate`.
2. Run `source-install-rc-closure-gate`.
3. Run `product-complete-closure-gate`.
4. Build the RC handoff pack.
5. Verify the handoff manifest.
6. Confirm `supportedClaims` and `sourceInstallRcClaim.claimedTargets` contain
   only targets with imported current-HEAD evidence.
7. Confirm `blockedClaims` and `noShipBlockers` are empty before any RC-ready
   statement.
