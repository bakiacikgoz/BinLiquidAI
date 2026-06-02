# Windows 2025 Canary Diagnostic

This note records the Design Partner RC phase 0 stabilization for the Operator
Panel navigation integration tests.

## Observed Failure

GitHub Actions run `26838502514` failed only on the canary job:

```text
Windows CI / Windows core and panel (windows-2025)
Error: Test timed out in 5000ms
apps/operator-panel/src/App.integration.test.tsx:54
```

The stable `windows-2022` job, Linux CI, and Operator Panel CI passed. The
failing test was a single broad browser-preview navigation integration test that
rendered the full app and clicked multiple route groups under the default Vitest
5 second timeout.

## Fix

- Split the broad navigation test into workspace, system, and governance route
  groups.
- Use async heading assertions after route clicks so slower Windows rendering is
  observed instead of raced.
- Apply an explicit `15_000ms` timeout only to these grouped navigation tests.
- Add route timing collection through
  `apps/operator-panel/scripts/collect-route-timings.ts`.
- Add `renderMs` to the productized-pages E2E manifest so route timing can be
  tracked as a release artifact.

## Diagnostic Artifact

Run:

```bash
corepack pnpm --dir apps/operator-panel routes:timings
```

Output:

```text
artifacts/operator-panel-ui/route-timings/route-timing-report.json
```

The script reads the latest productized-pages manifest when available. If no
manifest has been generated yet, it still writes a route inventory report with
`not_measured` rows.

## Boundary

This change does not alter production Operator Panel behavior. It stabilizes CI
signal and adds timing evidence for future route performance regressions.
