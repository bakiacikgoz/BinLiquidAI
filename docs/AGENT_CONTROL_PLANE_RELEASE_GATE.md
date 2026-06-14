# Agent Control Plane Release Gate

For the v1.0 pilot-readiness release candidate, the primary gate is:

```bash
make pilot-readiness-gate
```

The gate runs backend, frontend, Tauri bridge, evidence, i18n, raw JSON, and
claim-boundary checks in one command. It also writes the pilot readiness report
under `artifacts/pilot-readiness/`.

Focused gates remain useful while iterating:

```bash
make control-plane-gate
make control-plane-snapshot-gate
make evidence-pack-gate
make operator-panel-productization-gate
make operator-panel-tauri-smoke
make provider-native-gate
make provider-runtime-gate
make provider-workflow-proof-gate
make design-partner-rc-audit-gate
make design-partner-field-evidence-gate
make enterprise-gate
make pilot-gate
make ui-gate
make rust-gate
```

No ship if:

- `make pilot-readiness-gate` fails,
- `control-plane snapshot --json` reports silent fallback in live/Tauri mode,
- evidence verification fails or tamper verification unexpectedly passes,
- primary Operator Panel content exposes raw JSON,
- productized page screenshot coverage is missing,
- i18n dictionary or reason-code parity fails,
- provider native/runtime/workflow proof gates fail,
- provider evidence contains raw prompt, raw response, secret, or PII payloads,
- `design-partner-rc-audit-gate` reports blockers or unexpected warnings,
- `design-partner-field-evidence-gate` fails or strict RC promotion is not
  ready for target-environment evidence,
- claim guard allows unsupported desktop or live computer-use claims,
- Operator Console exposes live computer-use without qualification evidence,
- public desktop installer evidence is absent but the release is described as
  public desktop ready,
- target-environment signed qualification evidence is absent but enterprise Hat
  A readiness is described as fully ready.
# Governed Pilot Workflow

Release closure now includes the governed pilot workflow gate:

```bash
make governed-pilot-workflow-gate
```

The gate validates the workflow spec, runs deterministic memory/provider/approval evidence, verifies hash-only reports, regenerates schemas, and checks the Operator Panel route.

# Design Partner Field Evidence

Release closure also includes the target-environment field evidence gate:

```bash
make design-partner-field-evidence-gate
```

The gate prepares a target-environment session, collects hash-only field
evidence, verifies independent operator attestation, evaluates strict RC
promotion, generates the field pack, and checks the Operator Panel route.
