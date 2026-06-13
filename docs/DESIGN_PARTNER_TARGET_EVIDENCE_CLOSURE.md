# Design Partner Target Evidence Closure

Target evidence closure records a non-destructive rehearsal or target run without
persisting raw prompts, responses, screenshots, secrets, or PII.

Run the local rehearsal flow:

```bash
uv run python scripts/prepare_target_evidence_session.py \
  --profile enterprise \
  --mode rehearsal \
  --environment-label local-enterprise-rehearsal \
  --output-root artifacts/design-partner-target-evidence \
  --json

uv run python scripts/collect_target_evidence_rehearsal.py \
  --session artifacts/design-partner-target-evidence/session.json \
  --output-root artifacts/design-partner-target-evidence \
  --json

uv run python scripts/verify_target_evidence_bundle.py \
  --bundle artifacts/design-partner-target-evidence/target_evidence_bundle.json \
  --json
```

`make target-evidence-rehearsal-gate` wraps the same flow. Rehearsal evidence is
allowed to remain `conditional` because it is not a real design partner target
environment run. It must become `blocked` if any public/live claim boundary opens
or any raw/secret persistence flag is true.

Required closed boundaries:

- `public-desktop-installer`
- `live-macos-computer-use`
- `live-windows-computer-use`
- `live-linux-computer-use`

The bundle is hash-only. Evidence items contain artifact paths and sha256 hashes,
not raw provider payloads or screenshots.
