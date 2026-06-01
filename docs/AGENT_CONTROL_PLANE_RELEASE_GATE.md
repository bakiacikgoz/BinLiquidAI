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
- claim guard allows unsupported desktop or live computer-use claims,
- Operator Console exposes live computer-use without qualification evidence,
- public desktop installer evidence is absent but the release is described as
  public desktop ready,
- target-environment signed qualification evidence is absent but enterprise Hat
  A readiness is described as fully ready.
