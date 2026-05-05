# RFC Computer Use 004: Supervised macOS Vision Pilot

## Scope

This RFC defines the Phase 2 vision-first computer-use pilot. The pilot is a supervised macOS runtime path for safe local fixture tasks. It is not an unrestricted desktop automation product and does not qualify Windows or Linux live execution.

## Runtime Path

The runtime keeps the Phase 1 loop:

`observe -> interpret -> decide -> classify_risk -> approve_if_needed -> execute -> verify -> checkpoint`

Phase 2 adds guarded macOS capture/input adapters, strict local vision-provider parsing, replay verification, and deterministic qualification reporting.

## Safety Gates

- `vision_enabled=false` keeps the runtime unavailable.
- `vision_provider="none"` fails closed with `VISION_PROVIDER_UNAVAILABLE`.
- Windows live execution remains blocked with `WINDOWS_COMPUTER_USE_NOT_QUALIFIED`.
- Raw screenshots are not persisted by default; default persisted count is `0`.
- Terminal, sensitive, system/security, payment, password, wallet, key, and legal-consent surfaces stop or deny before execution.
- Risky actions produce approval snapshots and are not executed without a fresh matching approval contract.

## macOS Pilot Requirements

Live macOS use requires all of the following:

- `vision_enabled=true`
- `vision_provider="ollama"` or an equivalent local strict JSON provider
- `vision_model` configured
- `macos_live_enabled=true`
- Screen Recording permission granted manually
- Accessibility permission granted manually
- local qualification evidence

The runtime never attempts to grant permissions automatically.

## Provider Contract

The first local provider adapter is Ollama-compatible. The adapter accepts only strict JSON and maps invalid, timeout, and unavailable responses to deterministic fail-closed reason codes:

- `VISION_PROVIDER_INVALID_RESPONSE`
- `VISION_PROVIDER_TIMEOUT`
- `VISION_PROVIDER_UNAVAILABLE`

Screen text is treated as untrusted observed content, not an instruction.

## Non-Goals

- No Windows live automation support.
- No Linux live automation support.
- No unrestricted shell or terminal control.
- No claim that replay proves business correctness.
- No claim that deterministic mock qualification proves real-world reliability.
