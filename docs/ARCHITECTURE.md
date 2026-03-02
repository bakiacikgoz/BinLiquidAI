# ARCHITECTURE (v0.3)

## Product Path (Default)

1. User input is accepted by CLI.
2. Fast-path classifier optionally routes short/greeting inputs directly to `process_fast_chat`.
3. Normal path calls planner (strict JSON contract).
4. Active router selects expert path (`rule` in balanced by default).
5. Shadow router runs in parallel for telemetry-only comparison.
6. Expert execution is guarded by timeout, retries, tool budget, recursion limit, and circuit breaker.
7. LLM synthesizes final response.
8. Memory gate decides whether to persist memory candidate.
9. Tracer emits local telemetry (privacy-gated).

## Research Path

- Router telemetry dataset JSONL can be used to train/eval router calibration scripts.
- Research scripts are isolated under `research/sltc_experiments/`.
- Product runtime is not destabilized by research scripts.

## Core Components

- `binliquid/core/planner.py`: strict planner + deterministic fallback.
- `binliquid/core/orchestrator.py`: fallback logic, guardrails, synthesis, shadow metrics.
- `binliquid/governance/*`: policy engine, approval queue, audit/redaction pipeline.
- `binliquid/router/rule_router.py`: deterministic active routing baseline.
- `binliquid/router/sltc_router.py`: temporal/spiking-inspired router.
- `binliquid/experts/*`: typed expert payload producers.
- `binliquid/memory/*`: salience gate + store + retrieval ranking.
- `binliquid/telemetry/tracer.py`: trace events and router samples.

## Active vs Experimental

- Active (default): rule routing + sLTC shadow in balanced profile.
- Experimental: direct sLTC active routing in research profile.
- Deferred: desktop UI thin-shell.
