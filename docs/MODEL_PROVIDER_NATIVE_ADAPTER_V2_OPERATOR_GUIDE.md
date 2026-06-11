# Model Provider Native Adapter V2 Operator Guide

Scope: OpenAI Responses native adapter vertical slice.

## Status

- Adapter kind: `openai_responses`
- Runtime status: `canary_only`
- Default config state: disabled
- Live provider calls: disabled unless an operator explicitly opts in through the live canary controls
- Evidence mode: fixture or preview evidence only by default

This guide does not approve production routing for the native adapter. It describes the preview surface and the checks operators must see before a future graduation review.

## Safety Defaults

- Storage policy is `hash_only/store=false`.
- Raw prompt and raw response persistence is disabled.
- Provider-hosted tools, built-in tools, MCP tools, file search, web search, and computer-use tools are denied by default.
- Custom function tools are normalized as proposals only. The adapter must not execute proposed tools.
- Parallel tool calls are disabled in the native request payload.
- Live canary execution requires the existing double opt-in controls used by provider governance.

## Operator Panel Trust Fields

The provider registry payload uses `contractVersion="operator-panel.assistant-provider-models/v3"` for the native trust surface.

Expected OpenAI Responses preview row:

- `kind: openai_responses`
- `native: openai_responses: canary_only`
- `storage: hash_only/store=false`
- `server_tools: denied`
- `custom_tools: proposal_only`
- `source: fixture` or `source: preview`

Operators should treat any missing native metadata as not approved for native routing.

## CLI Checks

Run the offline native conformance matrix:

```bash
uv run python -m binliquid provider native conformance run --profile enterprise --json
```

Verify the saved native evidence:

```bash
uv run python -m binliquid provider native conformance verify \
  --output-root artifacts/model-provider-governance/native-v2 \
  --json
```

Run the full native adapter gate:

```bash
uv run python scripts/run_provider_native_adapter_gate.py --profile enterprise --json
```

The gate must report:

- `status=pass`
- at least 10 total conformance cases
- no unexpected failures
- no live canary attempt by default
- evidence verification passed

## Live Canary Boundary

Do not run a live OpenAI Responses canary unless all of these are true:

- operator intent is explicit for this run
- live canary flags are set deliberately
- budget and host allowlist checks pass
- evidence output path is isolated for review
- the result is treated as canary evidence, not production approval

## Blockers

Block release or rollout if any of these occur:

- `store=false` is not present in generated native payloads
- raw prompt or raw response content appears in evidence
- built-in, MCP, server-side, web search, file search, or computer-use tools are accepted
- custom function tool proposals are executed locally by the adapter
- secret-like output is persisted or returned as a successful case
- native conformance reports any unexpected failure
