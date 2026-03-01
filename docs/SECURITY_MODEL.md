# SECURITY_MODEL

## Varsayılan Güvenlik İlkeleri

- Web erişimi kapalı
- Kalıcı bellek kapalı
- Privacy mode açık (disk trace kapalı)
- Tool çağrıları orchestrator kontrolünde

> Not: `balanced` ve `research` profillerinde kalıcı bellek açılabilir; veri yalnızca yerel
SQLite dosyasına (`.binliquid/memory.sqlite3`) yazılır.

## Kod Çalıştırma ve Tool Katmanı

Bu MVP sürümünde tool katmanı read-only yerel arama odaklıdır. Yazma/komut çalıştırma
kabiliyetleri kapsam dışıdır.

## Injection Savunması

- Planner ve router JSON schema ile sınırlandırılmıştır.
- Serbest metin planner çıktısı parse edilemezse fallback çalışır.
- Doküman içeriği komut olarak yürütülmez.
