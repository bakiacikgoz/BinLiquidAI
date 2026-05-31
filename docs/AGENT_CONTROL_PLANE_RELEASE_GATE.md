# Agent Control Plane Release Gate

Run:

```bash
make control-plane-gate
make enterprise-gate
make pilot-gate
make ui-gate
make rust-gate
```

No ship if:

- control-plane doctor is blocked,
- enterprise signing is unavailable,
- policy fail mode is not fail-closed,
- evidence tamper verification does not fail,
- claim guard allows unsupported desktop or computer-use claims,
- Operator Console exposes live computer-use without qualification evidence.
