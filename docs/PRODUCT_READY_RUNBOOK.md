# Product Ready Runbook

1. Run first-run diagnostics:

   ```bash
   uv run binliquid setup first-run --profile enterprise --mode local-enterprise --json
   ```

2. Confirm assistant model/provider state:

   ```bash
   uv run binliquid assistant doctor --profile enterprise --json
   uv run binliquid assistant models --profile enterprise --json
   ```

3. Run product-complete closure:

   ```bash
   uv run python scripts/run_product_complete_closure_gate.py --profile enterprise --json
   ```

4. Treat any `noShipBlockers` as release-blocking.

External requirements remain outside this local proof: public signing,
notarization, customer pilot execution, and public cloud multi-tenant SaaS.
