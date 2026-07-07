# Platform Evidence Orchestrator

The platform evidence orchestrator turns local readiness runs into auditable,
target-scoped evidence bundles. A target is an OS and architecture tuple such as
`windows-x64`, `linux-x64`, `darwin-arm64`, or `darwin-x64`.

## Evidence Flow

1. Collect evidence on the target host:

   ```bash
   uv run binliquid local-product evidence collect --target current --profile enterprise --json
   ```

2. Export the manifest into a tamper-evident bundle:

   ```bash
   uv run binliquid local-product evidence export \
     --manifest artifacts/local-product/evidence/current/platform_evidence_manifest.json \
     --bundle artifacts/local-product/evidence-bundles/current.zip \
     --json
   ```

3. Verify the bundle before import:

   ```bash
   uv run binliquid local-product evidence verify \
     --bundle artifacts/local-product/evidence-bundles/current.zip \
     --json
   ```

4. Import and reconcile:

   ```bash
   uv run binliquid local-product evidence import \
     --bundle artifacts/local-product/evidence-bundles/current.zip \
     --json
   uv run binliquid local-product evidence reconcile --profile enterprise --json
   ```

The all-in-one local gate is:

```bash
uv run python scripts/run_platform_evidence_orchestrator_gate.py --profile enterprise --json
```

## Verification Rules

- The bundle index must match every file hash.
- The manifest target must match the expected target when provided.
- The manifest commit must match the expected commit when provided.
- Freshness is enforced by `maxAgeHours`; stale evidence is blocked.
- Raw prompts, provider payloads, secrets, and local absolute path leaks are
  treated as evidence verification failures.
- A supported target without imported evidence is `not_evidenced`, not failed.
- A claimed target without imported evidence creates
  `PLATFORM_CLAIM_WITHOUT_EVIDENCE`.

## CI

`.github/workflows/local-product-platform-evidence.yml` collects bundles on
hosted Windows, Linux, macOS arm64, and macOS x64 runners. The reconcile job only
claims targets that produced verified imported bundles for the current commit.
