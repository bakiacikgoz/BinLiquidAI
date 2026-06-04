# Agent Fallow Workflow

Use this workflow after changing Operator Panel TypeScript or JavaScript files.

## Required Commands

```bash
make operator-panel-fallow-gate
corepack pnpm --dir apps/operator-panel test
corepack pnpm --dir apps/operator-panel lint
```

For a focused changed-files audit:

```bash
FALLOW_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 \
corepack pnpm --dir apps/operator-panel exec fallow audit --format json --quiet --changed-since origin/main
```

## Review Order

1. Fix blocking errors first: unresolved imports, unlisted dependencies, duplicate exports, and boundary violations.
2. Review warn findings: unused files, unused exports, duplication, and health findings.
3. If a warning is intentional, document why in the handoff or with a narrow config entry.
4. Do not use broad ignore patterns for convenience.
5. Do not delete or rewrite code solely because Fallow suggests it.

## Auto-Fix Rule

Never run `fallow fix` without `--dry-run`.

Allowed:

```bash
FALLOW_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 \
corepack pnpm --dir apps/operator-panel exec fallow fix --dry-run --format json --quiet
```

Not allowed without explicit human approval:

```bash
corepack pnpm --dir apps/operator-panel exec fallow fix
```

## Handoff Format

Include this in the final engineering handoff when Operator Panel code changed:

```text
Fallow:
- Gate: pass/warn/fail
- Blocking reasons: none or list
- Warning buckets: dead_code=N, duplication=N, health=N
- Boundary violations: 0 required
- Artifact: artifacts/code-intelligence/fallow/SUMMARY.md
- Auto-fix: dry-run only, no source rewrite
```

## Optional MCP Note

Fallow provides MCP integration, but this repository's required gate is CLI-based so CI and local agent runs are deterministic.
