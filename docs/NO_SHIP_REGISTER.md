# No-Ship Register

The no-ship register is a machine-readable list of release boundaries that must not be confused with approval.

Default boundaries:

- `PUBLIC_MACOS_DESKTOP_WITHOUT_NOTARIZATION`
- `PUBLIC_WINDOWS_DESKTOP_WITHOUT_PUBLIC_GATE`
- `LIVE_WINDOWS_COMPUTER_USE_ENABLED`
- `LIVE_LINUX_COMPUTER_USE_ENABLED`
- `UNRESTRICTED_DESKTOP_AUTONOMY_CLAIM`
- `UNSIGNED_INTERNAL_ARTIFACT_PROMOTED`
- `RAW_OR_SECRET_ARTIFACT_DETECTED`
- `MISSING_HUMAN_SIGNOFF`
- `GATE_LEDGER_NOT_READY`
- `RC_FREEZE_NOT_RECONCILED`
- `LOCAL_PRODUCT_OVERBROAD_PLATFORM_CLAIM`
- `PLATFORM_CLAIM_WITHOUT_EVIDENCE`
- `PLATFORM_EVIDENCE_COMMIT_MISMATCH`
- `PLATFORM_EVIDENCE_TARGET_MISMATCH`
- `PLATFORM_EVIDENCE_SECRET_LEAK`
- `PLATFORM_EVIDENCE_STALE`
- `UNBOUNDED_PLATFORM_SUPPORT_CLAIM`
- `SOURCE_INSTALL_TARGET_WITHOUT_EVIDENCE`
- `SOURCE_INSTALL_TARGET_STALE`
- `SOURCE_INSTALL_TARGET_BLOCKED`
- `SOURCE_INSTALL_OVERCLAIM`

External Hat B blockers may be accepted boundaries for source/CLI RC. They remain blockers for public desktop release claims.

Platform/architecture targets without evidence should be reported as `not_evidenced`, not as supported. A broad CPU claim becomes no-ship only when the product text claims more targets than the evidence supports.
