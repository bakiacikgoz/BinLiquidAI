# UI Lab Integration Evidence

## Source and branch provenance

- UI Lab source: `/Users/baki/Documents/ImperaOS-UI-Lab`
- Frozen UI Lab source commit: `165208e90dd37376d5f0a21df22b7a1e7756aab5`
- Stacked base: `0a9c4ea5a6e26a3b32a9dd327ec1d7154ac39376`
- Integration branch: `codex/imperaos-ui-lab-full-integration-v1`

The Product Shell is authored under `apps/operator-panel/src/product-shell/`.
It does not import the UI Lab checkout, `src/mocks/**`, or `demoStore.ts`.
The UI Lab source remains unchanged.

## Product/runtime evidence

- The product router uses the desktop-safe hash router and preserves the old
  Operator Panel below `#/system/*`.
- Projects, tasks, task messages, links and preferences are SQLite-backed and
  exposed through the existing sidecar/Tauri bridge with idempotency binding.
- New work persists the initial user message, routes to the durable task ID,
  and starts the assistant session with the selected governed composer options.
- Existing Artifact Workspace controllers and all seven artifact editors remain
  canonical. Product-shell tabs host the Artifact Workspace, PTY terminals,
  native browser and registered preview surfaces.
- Browser origin policy is documented in
  `docs/security/BROWSER_ORIGIN_POLICY.md` and enforced by the native runtime.

## Mock/static guards

- `git diff --name-only origin/codex/imperaos-assistant-artifact-workspace-v1...HEAD`
  contains Product Shell and native runtime source.
- The same diff contains no `website/` path.
- A product-shell grep for `mockTasks`, `mockProjects`, `mockAgents`,
  `mockApprovals`, `mockArtifacts`, `demoScenarios` and `mockTerminal` returns
  no production match.

## Recent verification

- Operator Panel: 126 test files / 454 tests passed.
- Operator Panel lint and production build passed.
- Native browser policy unit tests: 3 passed.
- Native terminal policy/control tests: 2 passed; `cargo check` passed.
- Product workspace and Artifact RPC Python tests: 10 passed; Ruff passed.

## Explicitly open before V2 plan completion

- Project pin/archive/sort/pagination and native folder registration.
- Durable effort/speed/approval-profile task options and the full message action
  set.
- Project-root registration, terminal dock attachment and browser
  bounds/overlay/download-save coordination.
- Full branch/run/evidence context, data/files surfaces and collection-detail
  navigation.
