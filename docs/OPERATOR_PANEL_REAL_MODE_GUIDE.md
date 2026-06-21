# Operator Panel Real Mode Guide

Operator Panel product mode must not represent preview fixtures as live evidence.
Each visible primary action is classified in `apps/operator-panel/src/routeCapabilityMatrix.ts`.

Static enforcement:

```bash
corepack pnpm --dir apps/operator-panel exec tsx scripts/assert-no-inert-primary-actions.ts
```

Actions are valid only when classified as:

- `working`
- `disabled_with_reason`
- `preview_only`
