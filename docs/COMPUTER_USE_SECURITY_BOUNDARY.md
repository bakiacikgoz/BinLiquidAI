# Computer-Use Security Boundary

## Denied By Default

The vision-first computer-use runtime denies or stops before:

- terminal control unless policy changes from `deny`
- sensitive surfaces such as passwords, keychains, wallets, payments, and security settings
- stale approval snapshots
- invalid strict-JSON provider responses
- missing provider or missing permissions
- stale or mismatched qualification reports

## macOS Permission Boundary

BinLiquid can detect and report permission blockers. It must not grant permissions automatically or bypass macOS consent controls.

## Platform Boundary

macOS has a supervised qualification path. Windows and Linux remain:

```text
not_qualified / liveEnabled=false
```

No documentation or UI should claim unrestricted or cross-platform live desktop automation.
