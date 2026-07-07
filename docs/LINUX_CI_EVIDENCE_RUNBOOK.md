# Linux CI Evidence Runbook

Linux source install evidence is produced by the local product platform evidence
workflow on a hosted Linux runner.

```bash
gh workflow run local-product-platform-evidence.yml \
  --ref codex/remote-platform-evidence-harvest-source-install-rc-v1
uv run binliquid local-product ci harvest \
  --profile enterprise \
  --head-sha <commit-sha> \
  --json
```

If GitHub auth is unavailable, download the artifact bundle manually and use
`--manual-bundle`. A missing Linux artifact leaves `linux-x64` as
`not_evidenced`; it is not a product failure unless release text claims it.

