# TECHNICAL_SPEC_v2.0

## Product Path (MVP Faz 0-1)

- LLM core text/token-native (`lfm2.5-thinking:1.2b` via Ollama)
- Strict JSON planner output (`PlannerOutput`)
- Orchestrator with timeout, retry, fallback and circuit breaker
- Rule-based router (`RuleRouter`) + sLTC prototype router (`SLTCRouter`)
- Lightweight experts (`code_expert`, `research_expert`, `plan_expert`)
- Offline-first local tools
- Optional persistent memory with salience gate (`MemoryManager`)

## Research Path Boundary

Bu sürümde sLTC yalnızca interface seviyesindedir (`router/sltc_interface.py`).
Gerçek sLTC eğitim/çıkarım ve spike bridge ürün çekirdeğine dahil edilmez.
Ancak ürün yolunu bozmayan `SLTCRouter` prototipi ile C/D ablation çalıştırılır.

## Reliability Rules

1. Planner parse fail -> LLM-only direct path
2. Router confidence < 0.60 -> LLM-only
3. Expert timeout/error -> fallback expert veya LLM-only
4. Circuit breaker -> 3 ardışık hata sonrası 300s cooldown
