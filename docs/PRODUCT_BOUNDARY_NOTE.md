# Product Boundary Note

## Supported Positioning

ImperaOS is positioned as a:

> chat-first operator workspace for governed agent tasks, approvals and verifiable results

This implies:

- natural-language chat as a first-class control surface
- local or self-hosted capable operation
- policy-governed execution
- approval-aware mutations
- replayable and auditable traces
- visible action timelines and operator interrupts
- bounded agent execution surfaces in the current release
- enterprise qualification discipline

## Not Supported

ImperaOS should not be presented as:

- a consumer novelty chatbot
- a generic autonomous agent framework
- an uncontrolled browser/computer agent
- a digital worker that autonomously does everything without visibility or control

## UI Product Boundary

The operator panel is now a chat-first operator workspace. It is not a thin shell for every CLI command and not a hidden-autonomy surface.

Parity means workflow completion with transcript, approvals, state, timeline, and artifacts visible in one place.

## Optional Extension Boundary

Computer use is outside the core product. The retained implementation is an
optional distribution in `extensions/computer-use`, with active development
paused. The core UI and CLI do not offer desktop-control operations, and core
release gates do not require the extension or platform qualification.

Existing audit records and disabled capability fields remain readable for
compatibility. No historical qualification report enables a core desktop action.
See [Computer-use extension policy](COMPUTER_USE_EXTENSION.md).

## Provider Governance Layer Boundary

The model provider governance layer is a fail-closed registry, policy, redaction, and evidence boundary for model calls. It may be described as experimental/gated provider governance with local-first defaults and OpenAI-compatible adapter support.

It must not be described as:

- a key manager
- a cloud provider broker
- an unrestricted model proxy
- proof that remote/cloud providers are enabled by default
- proof that confidential data can automatically leave the local or self-hosted boundary

Remote/cloud provider calls require explicit configuration and remain disabled by default.
