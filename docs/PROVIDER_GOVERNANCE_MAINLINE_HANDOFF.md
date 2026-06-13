# Provider Governance Mainline Handoff

Provider Governance V1 should merge through PR review, not direct mainline
mutation. The branch carries OpenAI Responses and Anthropic Messages native
offline adapters, provider registry state, hash-only conformance artifacts,
Operator Panel Provider Trust visibility, and provider runtime dry-run proof.

Required PR checks:

- `make provider-native-gate`
- `make provider-runtime-gate`
- `make provider-workflow-proof-gate`
- `make design-partner-rc-audit-gate`
- `make pilot-readiness-gate`

Strict release behavior remains separate. `make design-partner-rc-gate` uses
`--fail-on-conditional`; conditional target-environment evidence can still make
that gate exit nonzero even when PR audit status is pass.

Boundaries that must remain closed:

- live computer-use without qualification
- public desktop installer claims without signed clean-machine evidence
- server-side provider tools
- custom provider tools executing directly instead of proposal-only
- raw prompt, response, secret, or PII persistence
