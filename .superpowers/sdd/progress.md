# ImperaOS UI Lab V2 integration ledger

## Phase 0 — stacked branch recovery

- Complete: static-export commit preserved at `backup/pr17-static-export-29be233`.
- Complete: integration branch reset to Artifact Workspace base `0a9c4ea5a6e26a3b32a9dd327ec1d7154ac39376`.

## Phase 1 — source freeze and shell scaffold

- Complete: UI Lab source frozen at `165208e90dd37376d5f0a21df22b7a1e7756aab5`.
- Complete: source Node tests (39), lint and production build passed.
- Complete: product-shell scaffold uses no UI Lab mock or demo-store imports.
- Verified: Operator Panel unit suite (441), lint and production build passed.

## Phase 2 — shell routing and design system

- Complete: desktop-safe HashRouter covers Product Shell task, collection, settings and system routes.
- Complete: persistent Product Shell-only preferences use `imperaos-product-shell-preferences-v2`.
- Complete: scoped dark/light visual tokens, sidebar width/collapse, rail and dock preferences are isolated from legacy settings.
- Verified: Operator Panel lint and production build passed.

## Phase 3 — Product Workspace domain

- In progress: workspace-scoped SQLite schema, project/task/message records, and service layer exist.
- Verified: unit test proves durable project/task/message creation and cross-workspace denial.
- Remaining: links/preferences service methods plus sidecar RPC, typed Tauri bridge, and frontend clients.
