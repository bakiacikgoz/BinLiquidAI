# Product Boundary Note

## Supported Positioning

AegisOS is positioned as a:

> chat-first operator-grade AI workstation with a governed computer-use runtime

This implies:

- natural-language chat as a first-class control surface
- local or self-hosted capable operation
- policy-governed execution
- approval-aware mutations
- replayable and auditable traces
- visible action timelines and operator interrupts
- bounded execution surfaces in the current release, with expansion toward full device control
- enterprise qualification discipline

## Not Supported

AegisOS should not be presented as:

- a consumer novelty chatbot
- a generic autonomous agent framework
- an uncontrolled browser/computer agent
- a digital worker that autonomously does everything without visibility or control

## UI Product Boundary

The operator panel is now a chat-first operator workspace. It is not a thin shell for every CLI command and not a hidden-autonomy surface.

Parity means workflow completion with transcript, approvals, state, timeline, and artifacts visible in one place.

## Computer Use Boundary

Computer use remains a supervised execution subsystem with:

- approval gates
- bounded allowlists
- replay and evidence
- fail-closed defaults

The current codebase still ships a bounded browser-first foundation. The product target is a broader desktop/browser/file runtime, but it must remain observable, interruptible, and fail-closed.
