# Operator Panel UI Eksik/Fonksiyon Dışı Kontrol Denetimi

Tarih: 2026-06-07

Kapsam: `apps/operator-panel` React/Tauri arayüzü, özellikle AI Assistant, üst chrome, composer, sağ rail ve ana sayfa aksiyonları.

## Uygulama Sonrası Kapanış Durumu

Bu denetim ilk keşif/baseline dokümanıdır. Aşağıdaki tablo, 2026-06-07 functional completion çalışmasından sonra her bulgunun son durumunu gösterir.

| ID | Son durum | Not |
| --- | --- | --- |
| UI-001 | Fixed | Assistant preview eventleri aynı reducer path üzerinden uygulanıyor; turn final/error/timeout ile sonlu state'e ulaşıyor. |
| UI-002 | Fixed | Python CLI -> Rust/Tauri bridge -> TypeScript bridge -> React model picker zinciri eklendi. |
| UI-003 | Accepted fail-closed | Assistant context search bu fazda execution surface değil; kontrol disabled ve açıklamalı tutuldu. |
| UI-004 | Accepted fail-closed | Arbitrary terminal ve assistant notification integration bu fazda kapsam dışı; kontroller güvenli disabled state'te kaldı. |
| UI-005 | Fixed | Attach context ve Tools güvenli allowlist seçimleri olarak composer state'e ve prompt builder'a bağlandı. |
| UI-006 | Fixed / deferred | Regenerate çalışır hale getirildi; share/more gerçek menü olmadığı için kaldırıldı veya explicit disabled bırakıldı. |
| UI-007 | Fixed / deferred | Sağ rail quick action'ları gerçek route/refresh davranışlarına indirildi; güvenli olmayan action yok. |
| UI-008 | Fixed | Compliance, recent sessions ve related artifact alanları fixture hard-code yerine mevcut run/claim/artifact state'inden besleniyor veya empty state gösteriyor. |
| UI-009 | Accepted fail-closed | Arbitrary terminal açma güvenlik nedeniyle bu fazda eklenmedi. |
| UI-010 | Fixed | Mission Control event filter gerçek state'e bağlandı. |
| UI-011 | Fixed | Load-more state/handler eklendi; ek veri yoksa kontrol açıklamalı disabled kalıyor. |
| UI-012 | Fixed | Raw JSON disabled sebebi görünür helper ile açıklandı. |
| UI-013 | Fixed | Computer-use blocker reason code'ları checklist'e dönüştürüldü. |
| UI-014 | Fixed | Operator ID eksikliği için Settings'e götüren CTA eklendi. |
| UI-015 | Fixed | `window.prompt` export akışı modal/sheet ile değiştirildi. |
| UI-016 | Fixed | Task safety checkbox değerleri submit options payload'una bağlandı. |

Kapanış doğrulaması:

- `corepack pnpm --dir apps/operator-panel qa:frontend`: geçti; UI control audit `148 controls, 0 critical, 0 high, 0 medium`.
- `uv run python -m pytest -q tests/test_operator_provider_models.py`: geçti.
- `cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml`: geçti.
- In-app Browser smoke: Assistant mesaj gönderimi terminal state'e ulaştı; `StartingStarting`/`Starting assistant turn` regression'ı görülmedi.

## Yöntem

- Kod taraması: `button`, `input`, `select`, `textarea`, `disabled`, `onClick`, `title`, `data-disabled-reason`, preview/fixture ve bridge akışları.
- Çalışan ekran kontrolü: `http://localhost:5173/` üzerinde DOM snapshot ve console health.
- Rota taraması: Dashboard, Agents, Çalıştırmalar, Onaylar, Evidence, Policy, Execution Surfaces, Mission Control, AI Assistant, Görevler, Sistem Sağlığı, Yürütmeler, Ayarlar, Loglar, Raporlar, Uyarılar, Planlamalar, Kullanıcılar, Roller, Politikalar.

Console sonucu: görünen ekranda `error`/`warn` logu yok. Bu, problemin framework crash değil, eksik/bağlanmamış ürün davranışı olduğunu gösteriyor.

## Öncelikli Bulgular

| ID | Öncelik | Alan | Kullanıcı Etkisi | Kanıt | Önerilen çözüm |
| --- | --- | --- | --- | --- | --- |
| UI-001 | P0 | AI Assistant cevap akışı | Kullanıcı mesaj gönderince assistant `Düşünüyor/starting` durumunda kalabiliyor; gerçek yanıt üretilmiyor gibi görünür. | Web preview için `startAssistantTurn` sadece `previewAssistantStartTurn` döndürüyor; event listener Tauri dışında no-op. `apps/operator-panel/src/bridge.ts:932`, `apps/operator-panel/src/bridge.ts:951`, `apps/operator-panel/src/assistant/assistantFixtures.ts:13` | Preview modda `previewAssistantEvents` olaylarını gerçekten dispatch/apply et veya web preview için açıkça "simülasyon" state'i göster. Tauri modda CLI stream kapanış/error olaylarının UI'da net görünmesini sağla. |
| UI-002 | P0 | AI Assistant model seçimi | Kullanıcı bilgisayardaki yüklü Ollama/Transformers modellerini göremiyor; model alanı manuel input gibi çalışıyor. | Composer provider listesi hard-coded; model alanı text input. `apps/operator-panel/src/components/assistant/AssistantComposer.tsx:88` | `bridge_assistant_models/list_models` benzeri bir endpoint ekle. Ollama için `ollama list`, Transformers için config/known local cache bilgisi döndür. Composer'da model seçici/autocomplete kullan. |
| UI-003 | P1 | Assistant üst arama / `⌘K` | `Search` ve `⌘K` görünüyor ama arama/komut paleti yok. Kullanıcı bunu çalışan global arama sanıyor. | Input doğrudan `disabled`. `apps/operator-panel/src/components/assistant/AssistantView.tsx:98` | Ya komut paleti/assistant context search implemente edilmeli ya da kontrol görünür UI'dan kaldırılmalı. Klavye kısayolu da gerçek handler'a bağlanmalı. |
| UI-004 | P1 | Assistant terminal ve bildirim ikonları | Üst chrome'da terminal ve bildirim ikonları tıklanabilir gibi duruyor ama kapalı. | İki kontrol de `disabled`. `apps/operator-panel/src/components/assistant/AssistantView.tsx:109`, `apps/operator-panel/src/components/assistant/AssistantView.tsx:112` | Entegrasyon yoksa assistant ekranında gizle; varsa shell sağ rail terminal/bildirim davranışı ile aynı aksiyona bağla. |
| UI-005 | P1 | Composer Attach / Tools | Attach context ve Tools butonları çalışmıyor. Kullanıcı tools seçimi, dosya/bağlam ekleme bekliyor. | İki buton da `disabled`; title "not available yet". `apps/operator-panel/src/components/assistant/AssistantComposer.tsx:138` | Tool picker, context attachment ve seçili tool state'i eklenmeli. Minimum çözüm: butonlar gizlenmeli veya "yakında" değil net disabled açıklaması tasarlanmalı. |
| UI-006 | P1 | Assistant mesaj aksiyonları | Kopyalama dışında paylaş, yeniden oluştur ve diğer aksiyonlar kapalı. | `AssistantMessage` içinde üç aksiyon `disabled`. `apps/operator-panel/src/components/assistant/AssistantMessage.tsx:132` | `regenerate` en azından son user mesajını yeniden göndermeli. Share/more aksiyonları ya gerçek menüye bağlanmalı ya kaldırılmalı. |
| UI-007 | P1 | Assistant sağ rail quick actions | "Create a new plan", "Check compliance status" gibi butonlar gerçek aksiyon değil; bazıları sadece refresh veya route değiştiriyor. | Hard-coded recent sessions ve quick actions. `apps/operator-panel/src/components/assistant/AssistantRightRail.tsx:170`, `apps/operator-panel/src/components/assistant/AssistantRightRail.tsx:187` | Bunları gerçek görev/plan oluşturma, inspection başlatma, compliance view filtreleme akışlarına bağla. Bağlanana kadar mock copy kaldırılmalı. |
| UI-008 | P2 | Assistant sağ rail sahte metrikler | Policy Compliance `98%`, recent sessions ve transcript artifact bilgileri hard-coded. | `Policy Compliance` sabit `98%`; recent sessions array'i sabit. `apps/operator-panel/src/components/assistant/AssistantRightRail.tsx:148` | Runtime snapshot/claims verisinden hesapla veya "veri yok" durumunu göster. |
| UI-009 | P1 | Right rail terminal | Genel sağ railde "Terminal Aç" kapalı; kullanıcı hızlı işlem bekliyor. | `terminalDisabled` her zaman true veriliyor. `apps/operator-panel/src/App.tsx:1400`, `apps/operator-panel/src/components/shell/RightRail.tsx:217` | Terminal entegrasyonu yapılacaksa bridge/launcher ekle; yapılmayacaksa butonu kaldır veya ayarlar/izin durumuyla koşullu göster. |
| UI-010 | P2 | Mission Control event filtering | "Tümü" filter kontrolü var ama filtreleme yok. | `SessionEventsCard` `onFilter` yoksa disabled. App bu prop'u vermiyor. `apps/operator-panel/src/components/mission/SessionEventsCard.tsx:15` | Event tag/status filtre state'i ekle veya filter butonunu kaldır. |
| UI-011 | P2 | Mission Control load more | "Daha fazla olay yükle" görünür ama kapalı; tail pagination yok. | `hasMore` default false ve `onLoadMore` yok. `apps/operator-panel/src/components/mission/SessionEventsCard.tsx:56` | Tail cursor üzerinden load-more veya infinite scroll ekle. Eklenene kadar butonu gizle. |
| UI-012 | P2 | Runtime raw JSON | Ham JSON butonu debugRaw kapalıyken devre dışı; açıklama sadece title. Touch/mobile kullanıcı açıklamayı göremeyebilir. | `debugRawEnabled` false ise disabled. `apps/operator-panel/src/components/mission/RuntimeSummaryCard.tsx:63` | Disabled state yanında görünür kısa açıklama veya settings'e götüren aksiyon ekle. |
| UI-013 | P1 | Görevler / Oturum başlat | "Oturum başlat" birçok capability blocker nedeniyle kapalı. Bu doğru olabilir ama kullanıcı hangi şartı nasıl çözeceğini ekranda işlem adımı olarak alamıyor. | Tarayıcı DOM title: `MACOS_COMPUTER_USE_NOT_QUALIFIED`, `COMPUTER_USE_EVIDENCE_MISSING`, `VISION_PROVIDER_UNAVAILABLE`, vb. App capability gate'i. | Blocker listesini aksiyonlanabilir checklist'e çevir: Ollama daemon, model varlığı, macOS capture/input backend, live config. |
| UI-014 | P2 | Onay aksiyonları | Operator ID yokken Onayla/Reddet/Yürüt disabled. İş kuralı doğru, ancak uyarı üst barda kalıyor; butonların yanında çözüm aksiyonu yok. | DOM: Onaylar route'unda üç buton disabled, reason `Devam etmek için operator id girin`. | Disabled alanına "Operator ID ayarla" CTA'sı ekle veya buton title yerine inline helper kullan. |
| UI-015 | P2 | Log/export aksiyonu | "Logları Dışa Aktar" tarayıcıda `window.prompt` ile hedef yol ister; modern UI yerine native prompt kullanıyor. | `onExportArtifacts` içinde `window.prompt`. `apps/operator-panel/src/App.tsx:972` | Modal/sheet tabanlı export formu ve son hedef klasör state'i ekle. |
| UI-016 | P2 | Görev güvenlik checkboxları | "Dış aksiyondan önce sor", "Silmeden önce sor", "Göndermeden önce sor" state'e yazılıyor ama submit payload'a veya runtime policy'ye bağlandığı görünmüyor. | State var ve checkbox değiştiriliyor; `onSubmitTask`/`onSubmitComputerUseSession` payload'ına aktarılmıyor. `apps/operator-panel/src/App.tsx:1628` | Bu seçimleri runtime submit options'a veya policy preview'e bağla. Bağlı değilse UI'dan kaldır. |

## Tarayıcıda Doğrulanan Devre Dışı Kontroller

### AI Assistant

- `Search assistant context`: disabled, "Assistant context search is not available yet".
- `Open terminal`: disabled, "Terminal access is not available in assistant preview".
- `Notifications`: disabled, "Assistant notifications are not available in this context".
- `More assistant actions`: disabled.
- `Attach context`: disabled, "Context attachment is not available yet".
- `Tools`: disabled, "Tool selection is not available yet".
- `Gönder`: assistant aktif/running state'te disabled, "Assistant is currently processing a turn."

### Mission Control

- `Onayla ve Devam Et`: operator ID yoksa disabled.
- `Reddet`: operator ID yoksa disabled.
- `Tümü`: event filtering yoksa disabled.
- `Daha fazla olay yükle`: ek event yok/handler yoksa disabled.
- `Ham JSON'u Görüntüle`: debugRaw kapalıysa disabled.

### Onaylar

- `Onayla`, `Reddet`, `Yürüt`: operator ID yoksa disabled.

### Görevler

- `Oturum başlat`: computer-use vision runtime capability gate geçmediği için disabled.

### Sağ Rail

- `Çalıştırmayı Devam Ettir`: görev spec yolu veya resumable session yoksa disabled.
- `Terminal Aç`: entegrasyon bağlı değil.
- `Çalıştırmayı İptal Et`: yalnızca aktif/stoppable computer-use oturumlarında çalışır.

## Mimari Eksikler

1. Assistant preview start response ile preview stream event'leri kopuk.
   `previewAssistantEvents` var ama web preview send akışında apply edilmiyor. Bu yüzden browser preview'da assistant gerçek cevap üretmiyor gibi kalıyor.

2. Model keşfi için frontend veya Tauri bridge kontratı yok.
   Runtime config resolve effective provider/model döndürüyor, fakat "kurulu modelleri listele" gibi bir API görünmüyor.

3. Birçok kontrol ürün niyeti gösteriyor ama veri/handler yok.
   Özellikle Assistant right rail hızlı aksiyonları, recent sessions, compliance yüzdesi ve related artifact alanları gerçek kaynakla beslenmiyor.

4. Disabled state açıklamaları çoğunlukla `title` attribute'a konmuş.
   Bu desktop hover'da kısmen çalışır; mobile/touch ve erişilebilirlik açısından yetersiz.

5. Bazı sayfalar gerçek workflow yerine "read-only productized page" gibi.
   Logs, Reports, Alerts, Plans, Users, Roles, Policy Packs sayfalarında tespit edilen disabled kontrol yok; ancak bunlar daha çok görüntüleme/listeme yüzeyi. Yönetim/filtre/oluşturma davranışı sınırlı.

## Önerilen Çözüm Sırası

1. P0: Assistant preview/runtime akışını düzelt.
   - Web preview'da `previewAssistantEvents` uygulanmalı.
   - Tauri stream error/final event'leri UI'da net durum bitişi üretmeli.
   - Running state sonsuz kalmamalı.

2. P0/P1: Model picker altyapısını ekle.
   - `bridge_assistant_models` veya `bridge_provider_models` komutu.
   - Ollama model listesi.
   - Config/effective provider ile uyumlu autocomplete/select.

3. P1: Assistant composer tool/context akışını gerçek hale getir.
   - Tool picker.
   - Context attachment.
   - Bağlam seçimi ve prompt builder'a aktarım.

4. P1: Mock/hard-coded assistant right rail alanlarını kaldır veya gerçek veriye bağla.

5. P1/P2: Disabled kontrollerde görünür inline açıklama ve ayara/aksiyona götüren CTA kullan.

6. P2: Mission Control event filtreleme/load-more davranışını ekle.

7. P2: Native prompt kullanan export akışını modal/sheet ile değiştir.

## Test/QA Notları

- `http://localhost:5173/` yüklendi.
- Sayfa başlığı: `operator-panel`.
- Console `warn/error`: 0.
- Rotalar DOM üzerinden gezildi ve devre dışı kontroller listelendi.
