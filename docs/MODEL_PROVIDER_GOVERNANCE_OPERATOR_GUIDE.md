# Model Provider Governance Operator Guide

This guide intentionally points operators to the current V1 runbook:

- [MODEL_PROVIDER_OPERATOR_GUIDE.md](MODEL_PROVIDER_OPERATOR_GUIDE.md)
- [MODEL_PROVIDER_GOVERNANCE.md](MODEL_PROVIDER_GOVERNANCE.md)
- [MODEL_PROVIDER_GOVERNANCE_V1_CLOSURE_REPORT.md](MODEL_PROVIDER_GOVERNANCE_V1_CLOSURE_REPORT.md)

Core operator rules:

- Do not put API key values in provider config files.
- Keep remote providers disabled unless an explicit local policy enables them.
- Use `provider policy simulate` before routing non-public data.
- Treat provider envelopes as audit metadata, not raw prompt/response storage.
- Run `scripts/run_provider_governance_gate.py` before merge or release claims.
