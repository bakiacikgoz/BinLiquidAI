# Deployment Guide

## Reference Deployment

### Linux Runtime Host

- dedicated service account
- encrypted local volume
- separate roots for config, stores, artifacts, and backups
- no inbound network listener unless explicitly approved
- enterprise profile as the default operating profile

### macOS Operator Workstation

- operator panel or CLI only
- no direct mutation authority outside CLI permission checks
- access limited to approved operator roles

## Deployment Steps

1. Install dependencies and application package.
2. Provision enterprise signing keys or KMS adapter.
3. Provision trusted verification keys.
4. Provision identity assertion path or IdP integration.
5. Resolve config and verify enterprise baseline.
6. Run backup, metrics snapshot, and GA readiness preflight.
7. Enable runtime traffic only after baseline passes.

## Environment Separation

Use separate roots per environment for:

- memory store
- approval store
- checkpoint store
- audit export
- team artifacts
- backups

Do not reuse the same paths between staging and production.

## Preflight Commands

```bash
uv run binliquid config resolve --profile enterprise --json
uv run binliquid security baseline --profile enterprise --json
uv run binliquid metrics snapshot --profile enterprise --json
uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json
```
