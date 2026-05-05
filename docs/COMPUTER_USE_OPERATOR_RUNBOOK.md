# Computer-Use Operator Runbook

## Daily Status Check

```bash
uv run binliquid computer-use doctor --platform all --json
uv run binliquid operator capabilities --json
```

Expected default:

```text
macOS: not_configured or not_qualified, liveEnabled=false
Windows: not_qualified, liveEnabled=false
Linux: not_qualified, liveEnabled=false
```

## macOS Qualification

1. Close unrelated sensitive windows.
2. Confirm Screen Recording and Accessibility are manually granted.
3. Configure a local strict-JSON provider.
4. Run the macOS doctor.
5. Run opt-in live qualification only under supervision.
6. Verify the report with:

```bash
uv run binliquid computer-use qualification verify \
  --platform macos \
  --report artifacts/computer_use/macos_qualification_report.json \
  --json
```

Replay/audit verification for the Phase 4B macOS report is separate:

```bash
uv run binliquid computer-use replay \
  --report artifacts/computer_use/macos_qualification_report.json \
  --verify \
  --json
```

The live fixture command requires both:

```text
BINLIQUID_COMPUTER_USE_LIVE_OPT_IN=I_UNDERSTAND_THIS_CONTROLS_MY_MAC
BINLIQUID_COMPUTER_USE_LIVE_MACOS=1
```

Without those values and a ready local provider, permissions, backends, matching
commit/config hash, and safety defaults, macOS remains blocked and
`liveEnabled=false`.

## Stop Conditions

Stop the run if a sensitive surface appears, an approval is stale, terminal control is requested, or raw screenshot persistence would be required by default.
