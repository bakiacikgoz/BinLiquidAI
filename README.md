# BinLiquid AI v2.0 (MVP Faz 0-1)

Offline-first, yerel çalışan hibrit asistan çekirdeği. Bu sürümde:

- `Ollama + lfm2.5-thinking:1.2b` LLM core
- Strict şema tabanlı planner
- Orchestrator + rule router + fallback + circuit breaker
- Hafif code/research/plan expert protokolü
- sLTC temporal router prototipi (Phase 3, product-safe)
- Kalıcı hafıza + salience gate (opsiyonel, profile ile)
- CLI (`doctor`, `chat`, `benchmark smoke`)
- Smoke benchmark (A/B/C/D ablation)

## Hızlı Başlangıç (macOS)

```bash
make bootstrap
make install
make doctor
make check
```

Tek mesaj denemesi:

```bash
uv run binliquid chat --profile lite --once "Bugünkü işleri 3 adımda planla"
```

Smoke benchmark:

```bash
uv run binliquid benchmark smoke --mode all --profile balanced
```

Hızlı kontrol (kısa):

```bash
uv run binliquid benchmark smoke --mode all --profile balanced --task-limit 2
```

10 ardışık chat stabilite kontrolü:

```bash
for i in {1..10}; do
  uv run binliquid chat --profile lite --once "Stabilite testi ${i}: kısa cevap ver."
done
```

Kalıcı hafıza istatistikleri:

```bash
uv run binliquid memory stats --profile balanced
```

## Önemli Varsayılanlar

- Web erişimi: kapalı
- Kalıcı bellek: kapalı
- Privacy mode: açık (kalıcı trace yok)
- Debug trace için: `--debug --privacy-off`

## Profiller

- `lite`: minimum kaynak, rule-router, kalıcı bellek kapalı
- `balanced`: sLTC router + kalıcı bellek salience gate
- `research`: debug ağırlıklı sLTC + geniş kaynak limitleri

## Dizinler

- `binliquid/`: çekirdek uygulama
- `benchmarks/`: smoke benchmark harness
- `docs/`: teknik spec, benchmark ve güvenlik dokümanları
