# Remote Platform Evidence Harvest Runbook

Remote harvest imports verified platform evidence bundles from CI, self-hosted
runners, or manually downloaded artifacts. GitHub auth is optional: if `gh` or
`GITHUB_TOKEN` is unavailable, the CLI returns a reason-coded diagnostic and the
manual bundle path remains available.

## Discover

```bash
uv run binliquid local-product ci discover \
  --branch codex/remote-platform-evidence-harvest-source-install-rc-v1 \
  --json
```

## Harvest

```bash
uv run binliquid local-product ci harvest \
  --profile enterprise \
  --head-sha <commit-sha> \
  --output-root artifacts/local-product/harvest \
  --json
```

## Manual Bundle Fallback

```bash
uv run binliquid local-product ci harvest \
  --profile enterprise \
  --head-sha <commit-sha> \
  --manual-bundle artifacts/local-product/evidence-bundles/<target>.zip \
  --json
```

Only verified bundles are imported. Auth failures and runner unavailability do
not create support claims.

