# Model Provider Security Review Packet

Scope: Model Provider Governance V1.1 canary and policy-aware routing shadow mode, plus the OpenAI Responses native adapter V2 offline vertical slice.

Security claims:

- Remote providers remain disabled by default.
- Live canaries require both CLI `--allow-live` and `BINLIQUID_PROVIDER_LIVE_CANARY=1`.
- Default CI uses offline fixtures only and performs no external provider calls.
- Public cloud providers cannot receive confidential, regulated, secret, credential,
  payment, or raw PII data classes.
- Canary evidence stores hashes and summaries, not raw prompts or raw responses.
- Evidence verification scans for secret markers, bearer tokens, authorization headers,
  raw-content keys, and email-like PII.
- Host allowlist checks run before adapter execution.
- Budget and rate-limit checks run before adapter execution.
- Router decisions are shadow-only and do not affect execution.
- OpenAI Responses native adapter remains canary-only and disabled by default.
- Native OpenAI Responses payloads force provider storage off with `store=false`.
- Provider-hosted tools, built-in tools, MCP tools, web search, file search, and computer-use tools are denied by default.
- Custom function tools are proposal-only and are not executed by the adapter.

Primary commands:

```bash
uv run python scripts/run_provider_governance_gate.py --profile enterprise --json
uv run python scripts/run_provider_canary_fixture.py --profile enterprise --json
uv run python -m binliquid provider canary verify \
  --evidence-root artifacts/model-provider-governance/canary \
  --json
uv run python scripts/run_provider_native_adapter_gate.py --profile enterprise --json
uv run python -m binliquid provider native conformance verify \
  --output-root artifacts/model-provider-governance/native-v2 \
  --json
```

Blocker conditions:

- Evidence verification fails.
- A public cloud provider is allowed for forbidden data classes.
- A live canary is attempted without both opt-in controls.
- Secret or PII markers appear in evidence.
- Host allowlist fails.
- Budget or rate-limit guard fails.
- Native evidence verification fails.
- A native payload permits provider storage, server tools, MCP tools, or built-in tools.

Known limits:

- OpenAI Responses native support is an offline canary-only vertical slice, not production routing approval.
- Anthropic, Gemini, and DeepSeek native adapters are not implemented here.
- Operator Panel is read-only for provider trust state; it does not trigger live canaries.
- Router shadow recommendations are not enforcement decisions.
