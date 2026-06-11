# RFC: Native Provider Adapter V2

Status: offline vertical slice implemented for OpenAI Responses preview.

## Goals

- Define a provider-native request and response contract without weakening V1 governance.
- Keep native adapters canary-only until live behavior is reviewed against current provider documentation.
- Deny provider-hosted/server-side tools by default.
- Preserve hash-only evidence rules.

## Non-Goals

- No Anthropic or Gemini native live adapter in V1.1.
- No live OpenAI Responses traffic by default.
- No server-side tool execution.
- No router shadow recommendation promoted to live routing.

## Contract

Schemas are generated from:

- `OpenAIResponsesRequest`
- `OpenAIResponsesResult`
- `ProviderStoragePolicy`
- `ProviderToolPolicyDecision`
- `ProviderToolProposal`
- `ProviderNativeConformanceReport`

Generated schema files:

- `contracts/model_providers/openai_responses_request.schema.json`
- `contracts/model_providers/openai_responses_result.schema.json`
- `contracts/model_providers/provider_storage_policy.schema.json`
- `contracts/model_providers/provider_tool_policy_decision.schema.json`
- `contracts/model_providers/provider_tool_proposal.schema.json`
- `contracts/model_providers/provider_native_conformance_report.schema.json`

## Policy Defaults

- `canary_only = true`
- `server_tools_allowed = false`
- `approval_required = true`
- raw content persistence disabled
- OpenAI Responses payloads force `store=false`
- parallel tool calls are disabled
- custom function tools are proposal-only

## Adapter Inventory

| Provider family | V2 status |
| --- | --- |
| OpenAI Responses | disabled-by-default offline vertical slice |
| Anthropic native | RFC only |
| Gemini native | RFC only |
| DeepSeek | OpenAI-compatible recipe only |

## Gate

The native adapter gate is:

```bash
uv run python scripts/run_provider_native_adapter_gate.py --profile enterprise --json
```

The gate requires at least 10 offline conformance cases, no unexpected failures, no live canary attempt by default, and hash-only evidence verification.

## Graduation Requirements

1. Official provider API shape reviewed for the exact version used.
2. Contract fixtures added for success, refusal, rate limit, timeout, schema mismatch, and tool proposal.
3. Canary budget and network gates pass.
4. Evidence verifier confirms no secret or raw content markers.
5. Operator Panel marks native status as preview until live evidence exists.
