# macOS Computer-Use Qualification Guide

## Scope

This guide covers supervised local macOS qualification only. It is limited to safe local fixtures such as local text editing, local file visibility checks, local HTML forms, scroll verification, and approval-stop checks.

## Manual Prerequisites

The operator must grant permissions manually in macOS settings:

- Screen Recording
- Accessibility

BinLiquid must never edit TCC databases, run `sudo`, ask for an admin password, or use private APIs to bypass consent.

## Config

Defaults are fail-closed:

```toml
[computer_use]
vision_enabled = false
vision_provider = "none"
vision_model = ""
macos_live_enabled = false
macos_capture_backend = "disabled"
macos_input_backend = "disabled"
macos_require_fresh_qualification = true
macos_qualification_report = ""
raw_screenshot_persistence = false
raw_screenshot_max_count = 0
terminal_control = "deny"
sensitive_surface_policy = "stop"
```

## Qualification

Run the doctor first:

```bash
uv run binliquid computer-use doctor --platform macos --json
```

Run live qualification only on a prepared, supervised local desktop:

```bash
BINLIQUID_COMPUTER_USE_LIVE_MACOS=1 \
BINLIQUID_COMPUTER_USE_SUPERVISED_FIXTURE_ONLY=1 \
BINLIQUID_COMPUTER_USE_REQUIRE_STEP_APPROVAL=1 \
BINLIQUID_COMPUTER_USE_ACK="I understand BinLiquid will control my macOS desktop only for local supervised fixtures." \
uv run binliquid computer-use qualification run \
  --platform macos \
  --suite live-fixture-smoke \
  --mode supervised \
  --output artifacts/computer_use/macos_qualification_report.json \
  --json
```

Run preflight first when preparing a host:

```bash
uv run binliquid computer-use qualification run \
  --platform macos \
  --suite live-fixture-smoke \
  --mode preflight \
  --output artifacts/computer_use/macos_qualification_report.json \
  --json
```

If the explicit opt-in, acknowledgment, supervised-fixture scope, step approval,
or any readiness gate is missing, the command writes a blocked report with local
fixture metadata only. It does not request permissions, grant permissions,
persist raw screenshots, or enable live runtime execution.

Verify report replay integrity separately:

```bash
uv run binliquid computer-use replay \
  --report artifacts/computer_use/macos_qualification_report.json \
  --verify \
  --json
```

A fresh passing report without `macos_live_enabled=true` may report
`fixture_qualified` with `fixtureQualified=true`, `productionQualified=false`,
and `liveEnabled=false` by default. macOS supervised local fixture
qualification is not unrestricted desktop automation, and it does not qualify
Windows or Linux live computer-use.
