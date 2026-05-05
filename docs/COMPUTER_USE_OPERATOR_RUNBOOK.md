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

## Stop Conditions

Stop the run if a sensitive surface appears, an approval is stale, terminal control is requested, or raw screenshot persistence would be required by default.
