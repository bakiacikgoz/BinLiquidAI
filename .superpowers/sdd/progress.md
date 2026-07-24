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

- Complete: workspace-scoped SQLite project/task/message/link/preference records, including durable project root references, pin state, manual order and archive metadata, exist.
- Complete: existing sidecar RPC, typed Tauri bridge and frontend client use idempotency-bound mutations.
- Verified: durable project/task/message creation, replay idempotency and cross-workspace denial tests pass.

## Phase 4–6 — Product navigation, task lifecycle and conversation

- Complete: sidebar loading, project selection, real first task/message persistence, task-session routing and global search use governed sources.
- Complete: task composer uses the existing model inventory/runtime transport and carries validated context/tool controls into the first turn.
- Complete: effort, speed and approval-profile choices persist with each task, traverse the governed bridge, and affect CLI execution. Fast selects the fast-chat router path; always-ask creates a governance approval or fails closed; automatic never broadens policy authority.
- Complete: persisted transcript projection avoids duplicate runtime turns; assistant artifacts open the governed workspace tab.
- Complete: sidebar project pages use bounded cursor pagination, durable pin/archive/manual ordering and native folder registration through opaque tickets; no renderer or sidecar response carries the local path.
- Complete: conversation copy, cancel and regenerate actions are wired to the native clipboard, assistant cancellation and governed runtime respectively.
- Remaining: the complete message action set beyond these core actions.

## Phase 7 — Workspace and artifacts

- Complete: artifact, terminal, browser and preview surfaces use a governed workspace tab lifecycle; runtime tab IDs are unique.
- Complete: existing Artifact Workspace controller/editor is reused rather than copying a mock editor.
- Complete: an assistant artifact card transfers its exact artifact ID into the
  canonical Artifact Workspace tab and focuses that persisted artifact.
- Remaining: add the minimal governed files/data surfaces.

## Phase 8–9 — Native runtime surfaces

- Complete: user PTY uses an application-owned verified root, resize, interrupt, kill and tab-scoped cleanup.
- Complete: browser policy is mode-scoped; user HTTPS, registered preview origins, agent allowlists, redirect rechecks, isolated agent data stores and approval-gated external effects are enforced.
- Complete: blocked content/internal schemes cannot be reclassified as
  approval-gated external applications; agent allowlists reject localhost and
  literal IP addresses.
- Remaining: terminal attachment to the registered project root, browser bounds/overlay coordination, history controls where the Tauri runtime exposes them, and governed download save approval.

## Phase 10–12 — Product collections and settings

- Complete: real artifact, approval and agent collections use their existing bridges; automation remains honestly unavailable in this desktop runtime.
- Complete: product settings writes the existing operator profile and preserves a direct legacy-system route.
- Remaining: richer task evidence/run/branch context, full collection detail navigation and centralized shortcuts/profile controls.
