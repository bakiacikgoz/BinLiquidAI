# macOS Local Evidence Runbook

Use this on the Mac that will produce `darwin-arm64` or `darwin-x64` source
install evidence.

```bash
git checkout codex/remote-platform-evidence-harvest-source-install-rc-v1
uv sync --python 3.11 --extra dev
uv run binliquid local-product evidence collect --target current --profile enterprise --json
uv run binliquid local-product evidence export \
  --manifest artifacts/local-product/evidence/current/platform_evidence_manifest.json \
  --bundle artifacts/local-product/evidence-bundles/darwin-arm64.zip \
  --json
```

Copy only the generated evidence bundle back to the release workspace, then run:

```bash
uv run binliquid local-product ci harvest \
  --manual-bundle artifacts/local-product/evidence-bundles/darwin-arm64.zip \
  --head-sha <commit-sha> \
  --json
```

This does not enable public notarized desktop installer claims or live
computer-use claims.

