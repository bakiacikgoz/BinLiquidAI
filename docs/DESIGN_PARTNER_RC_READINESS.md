# Design Partner RC Readiness

Run the focused release-candidate gate before a design partner handoff:

```bash
make design-partner-rc-gate
```

The gate writes `artifacts/design-partner-rc/manifest.json` and
`artifacts/design-partner-rc/DESIGN_PARTNER_RC_REPORT.md`.

Boundary rules:

- Computer-use live execution remains blocked.
- Public desktop installer readiness remains blocked.
- Preview fixtures must not be presented as live evidence.
- Destructive operations are dry-run or blocked only.

