# Pilot Local Computer Control Smoke

Bu smoke akisi, Sprint 6.2 ile gelen bounded local-control slice'i dogrulamak icindir.

## Gereksinimler

- macOS
- `computer-use readiness` sonucu `ready` veya acik yerel izinlerle `degraded`
- Finder ve TextEdit kurulu
- Accessibility ve AppleScript automation izinleri acik
- Scoped test dosyalari allowed roots altinda

## Desteklenen bounded komutlar

- `finder_reveal "/path/to/file.txt"`
- `finder_rename "/path/to/file.txt" to "renamed.txt"`
- `finder_move "/path/to/file.txt" to "/path/to/destination"`
- `textedit_open "/path/to/file.txt"`
- `textedit_append "note text"`
- `textedit_append "note text" to "/path/to/file.txt"`
- `textedit_save`
- `textedit_save "/path/to/file.txt"`

## Smoke 1: Finder

1. Allowed root altinda bir dosya olustur.
2. Chat/request paneline su akisi ver:

```text
finder_reveal "/allowed-root/incoming/report.txt"
finder_rename "/allowed-root/incoming/report.txt" to "report-reviewed.txt"
finder_move "/allowed-root/incoming/report-reviewed.txt" to "/allowed-root/processed"
```

Beklenen:

- Session tamamlanir.
- `processed/report-reviewed.txt` olusur.
- Timeline Finder adimlarini verified olarak gosterir.
- `world_model.selected_paths` son dosyayi isaret eder.

## Smoke 2: TextEdit

1. Allowed root altinda `notes.txt` olustur.
2. Chat/request paneline su akisi ver:

```text
textedit_open "/allowed-root/notes.txt"
textedit_append " local review"
textedit_save "/allowed-root/notes.txt"
```

Beklenen:

- Session tamamlanir.
- Dosya icerigi guncellenir.
- `world_model.active_document_path` `notes.txt` olur.

## Smoke 3: Browser + Local

1. Mevcut upload/download fixture veya local smoke site acik olsun.
2. Chat/request paneline su akisi ver:

```text
open "http://127.0.0.1:PORT/index.html"
download "#download" to "/allowed-root/downloaded.txt"
textedit_open "/allowed-root/downloaded.txt"
textedit_append " reviewed"
textedit_save "/allowed-root/downloaded.txt"
```

Beklenen:

- Download artifact olusur.
- TextEdit dosyayi acip gunceller.
- `filesystem_result_set` icinde indirilen dosya gorunur.

## Dürüst boundary

- Bu slice Finder ve TextEdit ile sinirlidir.
- Genel amacli herhangi bir native app icin parity yok.
- Sensitive local actions icin approval/policy matrisi henuz erken asamadadir.
- Cross-platform parity yok.
