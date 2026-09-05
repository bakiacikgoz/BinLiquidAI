# Agent onboarding

Before changing the desktop UI, read [the design and handoff guide](docs/UI_DESIGN_AND_HANDOFF.md). It records accepted user preferences, architecture, regression lessons and remaining limitations. Preserve these decisions across machines and agents; update the guide when behavior changes.

## CodeGraph

When `.codegraph/` exists, use `codegraph explore "<symbols or question>"` (or the `codegraph_explore` MCP tool) before grep/find or reading unfamiliar code. If no index exists, skip CodeGraph; do not index without the user's request.

## Working boundaries

- Keep frozen `apps/operator-panel/src/product-shell/styles/ui-lab/{tokens,globals,surfaces}.css` unchanged. Product adaptations belong in `styles/shell.css`.
- Use real runtime state and governed capabilities. Never simulate model availability, thinking, terminal output, git statistics or working actions to match a screenshot.
- Validate layout through the real AppShell, including narrow conversation widths with workspace and bottom terminal open.
- Preserve unrelated working-tree changes. Do not commit local caches, credentials, runtime state or clipboard attachments.
- Record actual checks and known gaps; screenshots and mocked browser tests do not prove native PTY or provider integration.
