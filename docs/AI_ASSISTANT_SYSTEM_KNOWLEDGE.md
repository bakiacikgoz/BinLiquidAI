# AI Assistant System Knowledge

This is the canonical local source for grounding AegisOS Assistant answers about the
BinLiquid/AegisOS product. Treat this document as product knowledge, not as an instruction
to bypass runtime policy.

## AegisOS Identity

AegisOS on BinLiquid is a self-hosted, single-organization enterprise Agent Control Plane.
It is not a generic security-monitoring product. The product coordinates governed agents,
policy decisions, approvals, evidence, memory boundaries, provider governance, and
operator-facing runtime diagnostics.

## Product Boundary

Product mode must not use fake assistant answers or preview-only model discovery. If runtime
setup is incomplete, the assistant must return setup-required diagnostics from `assistant doctor`
or system knowledge doctor output. Public web search is not part of the local product knowledge
path.

## Giving An Agent A Task

To give an agent a task, first register or verify the agent in the Agent Control Plane, then
submit a governed request through the external agent gateway or control-plane run surface.
Read-only requests can proceed when policy allows them. External writes, sensitive actions,
and destructive operations require approval and evidence gates.

Useful commands include:

```bash
uv run binliquid control-plane agent register --profile enterprise --spec examples/external-agent/sample_stdio_agent.json --json
uv run binliquid control-plane gateway submit-v1-1 --profile enterprise --request examples/external-agent/request_v1_1_read_only.json --json
uv run binliquid control-plane run submit --profile enterprise --agent-id governed-ops --prompt "Inspect alerts and summarize read-only findings" --operator-id ops-team-01 --json
```

Grounding sources:

- `docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md`
- `docs/AGENT_CONTROL_PLANE_ADAPTER_CONTRACT.md`
- `docs/AGENT_CONTROL_PLANE_ARCHITECTURE.md`

## External Agent Gateway

The external gateway accepts governed external agent requests only after enrollment and policy
checks. Unknown or unenrolled agents must be denied. Requests must keep input and identity
bound to evidence-friendly hashes and runtime records.

## Approval Lifecycle

Approval is the boundary between proposed work and executed work. The assistant may explain
or draft a remediation plan, but action execution remains gated by pending, approved, executed,
and consumed approval states. Mutating work should be described as dry-run or proposal-only
until approval is reviewed.

## Runs, Evidence, And Replay

Run answers should use visible runtime context plus local docs. When asked why a run is blocked,
combine run status, normalized events, approval state, and evidence references. Do not invent
hidden runtime state.

## Memory Boundaries

System knowledge is separate from user memory and workspace memory. Raw memory content is not
indexed into the assistant system knowledge corpus. Memory answers should refer to policy,
scope, and authority docs rather than private memory records.

## Provider Governance

Provider setup and routing are governed by model-provider registry, policy, doctor, and canary
surfaces. If a provider is missing or disabled, the assistant should explain the setup-required
state and suggest provider doctor commands instead of pretending a model is available.

Useful commands include:

```bash
uv run binliquid assistant models --profile enterprise --json
uv run binliquid assistant doctor --profile enterprise --json
uv run binliquid provider doctor --profile enterprise --json
```

## Computer-Use Boundaries

Computer-use is qualification-gated and fail-closed. The assistant may explain readiness,
approval, and evidence requirements, but it must not claim unrestricted live control. Platform
qualification and approval state determine whether a computer-use run can proceed.

Useful commands include:

```bash
uv run binliquid computer-use doctor --profile enterprise --json
make macos-local-trial-gate
```

## First Run And Local Trial

First-run readiness should be diagnosed with setup and product gates. Mac M4 local trial work
is evidence-gated and should be described as a local qualification path, not as public release
proof.

Useful commands include:

```bash
uv run binliquid setup first-run --profile enterprise --json
make first-run-readiness-gate
make assistant-system-knowledge-gate
```

## Where The Assistant Knowledge Comes From

When asked "Where do you know this from?" or "Bunu nereden biliyorsun?", the assistant should
answer that AegisOS platform usage is grounded in local system knowledge built from repo docs,
contracts, CLI surfaces, route/capability manifests, and visible runtime snapshots. It should
not answer that it knows the product from broad training data.
