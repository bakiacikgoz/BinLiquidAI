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

Replay/audit verification for the macOS qualification report is separate:

```bash
uv run binliquid computer-use replay \
  --report artifacts/computer_use/macos_qualification_report.json \
  --verify \
  --json
```

The live fixture command requires all of:

```text
BINLIQUID_COMPUTER_USE_LIVE_MACOS=1
BINLIQUID_COMPUTER_USE_SUPERVISED_FIXTURE_ONLY=1
BINLIQUID_COMPUTER_USE_REQUIRE_STEP_APPROVAL=1
BINLIQUID_COMPUTER_USE_ACK=I understand BinLiquid will control my macOS desktop only for local supervised fixtures.
```

Without those values and a ready local provider, permissions, backends, matching
commit/config hash, and safety defaults, macOS remains blocked and
`liveEnabled=false`. Blocked preflight reports can still replay-verify
successfully for audit integrity; qualification pass/fail is reported
separately as `qualificationPassed`.

## Stop Conditions

Stop the run if a sensitive surface appears, an approval is stale, terminal control is requested, or raw screenshot persistence would be required by default.
