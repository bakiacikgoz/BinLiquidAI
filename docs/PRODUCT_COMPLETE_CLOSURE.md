# Product-Complete Closure

The product-complete closure gate is the top-level local proof for BinLiquid /
AegisOS as a self-hosted single-organization enterprise Agent Control Plane.

Canonical command:

```bash
uv run python scripts/run_product_complete_closure_gate.py --profile enterprise --json
```

The gate aggregates:

- Product scope and no-ship register.
- Real assistant runtime diagnostics.
- Assistant system knowledge grounding.
- Assistant governed tasking gate.
- Operator Panel route/action productization.
- First-run readiness diagnostics.
- Local product platform/architecture readiness and claim boundary.
- Platform evidence reconciliation for imported target bundles.
- Remote platform evidence harvest, source install RC claim, target closure
  actions, and release claim accuracy.
- Enterprise workspace onboarding.
- Governed agent workflow smoke.
- Evidence/release closure.

Generated artifacts:

- `artifacts/product-complete-closure/product_complete_closure_report.json`
- `artifacts/product-complete-closure/product_complete_closure_report.md`
- `artifacts/product-complete-closure/product_complete_pr_body.md`
- `artifacts/product-complete-closure/no_ship_register.json`

The `localProductReadiness` field reports the current target, evidenced supported claims, and not-evidenced targets. The `platformEvidenceReconciliation` field reports imported evidence by target and emits no-ship blockers for claimed targets without matching evidence. The `sourceInstallRcClaim` and `releaseClaimAccuracy` fields restrict source install release wording to verified current-commit targets. Not-evidenced targets are not product failures; they are unsupported claims until evidence exists.
