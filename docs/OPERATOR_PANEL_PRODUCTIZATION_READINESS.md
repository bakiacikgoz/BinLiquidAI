# Operator Panel Productization Readiness

This document records the v1 productization slice for the self-hosted Agent Control Plane Console.

## Scope Completed

- Sidebar navigation is backed by `apps/operator-panel/src/routeRegistry.ts`.
- Every visible navigation item has a unique route id, label, and heading.
- Visible alias navigation has been removed:
  - Logs no longer opens Runs.
  - Reports, Alerts, Users, Roles, and Policy Packs no longer open Operations.
  - Plans no longer opens Tasks.
- Productized page shells exist for Logs, Reports, Alerts, Plans, Users, Roles, and Policy Packs.
- Dashboard, Agents, Evidence, Policy Simulation, and Execution Surfaces have richer product states instead of single-line placeholders.
- Computer-use live execution remains qualification-gated; the Execution Surfaces page does not expose an enabled live-start action.

## Gate

Run:

```bash
make operator-panel-productization-gate
```

The gate runs:

- `pnpm test`
- `pnpm lint`
- `pnpm build`
- `pnpm test:e2e`
- `tsx scripts/assert-productized-pages.ts`

The E2E productization spec writes:

```text
artifacts/operator-panel-ui/productized-pages/manifest.json
artifacts/operator-panel-ui/productized-pages/screenshots/*.png
```

The manifest must report:

- `aliasViews: []`
- `consoleMessages: []`
- `pageErrors: []`
- one screenshot-backed entry per visible route

## Remaining Product Risks

- Runs, Approvals, System, and Operations still retain some raw JSON debug surfaces for compatibility with existing tests and bridge workflows.
- Full i18n normalization is not complete; technical headings remain English in several established views.
- Operations destructive commands remain bridge-gated and preview-safe, but deeper permission-specific UI affordances should be expanded in a later hardening pass.
