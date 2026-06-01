# I18N And Copy Guide

The Operator Panel supports English and Turkish UI copy. User-facing product
copy should come from the shared dictionaries or from localized reason-code
helpers.

## Source Files

```text
apps/operator-panel/src/i18n.ts
apps/operator-panel/src/control-plane/reasonCodes.ts
apps/operator-panel/scripts/assert-i18n-coverage.ts
```

## Rules

- Keep dictionary keys identical for `en` and `tr`.
- Keep reason-code keys identical for `en` and `tr`.
- Internal reason codes may remain uppercase English identifiers.
- User-facing explanations for reason codes must be localized.
- Empty dictionary values are gate failures.
- Avoid mixing Turkish navigation with English explanatory copy unless the text
  is an internal identifier, command, status code, or API field name.
- Debug/raw inspectors may expose technical keys; primary product surfaces
  should explain the decision in human terms.

## Gate

Run:

```bash
corepack pnpm --dir apps/operator-panel i18n:coverage
```

The full release gate also runs:

```bash
make pilot-readiness-gate
```

## Reason-Code Copy Pattern

Use `formatReasonCode`, `formatReasonCodeList`, or `getReasonCodeMessage`
instead of rendering raw blocker arrays directly in primary UI.

Good primary copy:

```text
MACOS_LIVE_DISABLED: Live macOS computer-use is disabled for this scope.
```

Allowed debug copy:

```json
{ "reasonCodes": ["MACOS_LIVE_DISABLED"] }
```

## Current Boundary Copy

The following boundary messages must stay explicit:

- Preview fixture data is not live evidence.
- Computer-use live execution remains qualification-gated.
- Public desktop readiness requires signed clean-machine evidence.
- Missing metrics or qualification evidence must not be described as healthy.
