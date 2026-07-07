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

4. Run the macOS Apple Silicon local trial gate when preparing a personal
   source/dev trial. An M4 device is only an example local validation target:

   ```bash
   uv run python scripts/run_macos_local_trial_gate.py --profile enterprise --json
   ```

   `conditional` means the local source trial can continue with explicit setup
   notes, such as missing assistant model/provider readiness. It is not a public
   desktop release signal.

5. Treat any `noShipBlockers` as release-blocking.

External requirements remain outside this local proof: public signing,
notarization, customer pilot execution, and public cloud multi-tenant SaaS.
