# ImperaOS arayüz tasarımı ve ajan devir rehberi

Bu belge 5 Eylül 2026 tarihindeki kullanıcı tercihlerini ve uygulama sırasında öğrenilenleri taşır. Başka bir bilgisayarda çalışmaya başlamadan önce bunu ve kökteki AGENTS.md dosyasını okuyun. Eski sohbet ekran görüntülerindeki başarı iddiaları test kanıtı değildir.

## Tasarım dili

Kullanıcı kompakt, sakin, Codex benzeri koyu bir masaüstü arayüzü istiyor. Büyük mavi kartlar, teknik durum rozetleri ve kalın araç çubukları uygun değil. Ürün adı ImperaOS olarak kalır.

| Alan | Kabul edilen ölçü / görünüm |
|---|---|
| Ana yüzey, terminal, workspace | `#181818` |
| Sidebar | macOS: native Sidebar vibrancy üzerinde saydam koyu/açık yüzey; diğer platformlar ve web: `#202020`; hover/seçim düşük opaklıklı |
| Kartlar / ayırıcılar | Yaklaşık `#2b2b2b` / `#303030`, düşük kontrast |
| Üst başlık | 46 px; 13 px başlık; 28 px simge düğmeleri |
| Sohbet ve composer | 736 px azami içerik genişliği; dış alanda 24 px boşluk |
| Kullanıcı mesajı | En fazla 515 px / %72; 18 px köşe; 13 px metin |
| Composer | Yaklaşık 96 px asgari yükseklik; yeni sohbette 38 px proje şeridi |
| Yeni sohbet önerileri | 110 px asgari yükseklik; 14 px padding; 10 px aralık |
| Workspace sekmeleri | 28 px, 10 px köşe, kısaltılmış başlık ve tam ad tooltip |
| Terminal | 12 px monospace, 1.2 satır yüksekliği, `#e6e6e6` yazı |
| Tarayıcı | 42 px araç çubuğu, 28 px adres alanı, koyu boş durum |

Frozen UI Lab CSS dosyalarını değiştirmeyin. Ürün uyarlamaları `apps/operator-panel/src/product-shell/styles/shell.css` içinde tutulur. Yeni CSS eklerken eski geçersiz kılmalarla çakışmayı kontrol edin.

## Davranış sözleşmesi

- Görevlerden yeni sohbet açıldığında yalnızca **Proje seç** görünür; kendiliğinden proje, Yerel veya branch seçilmez. Aranabilir küçük proje listesi ve gerçek klasör seçimiyle Yeni proje çalışır. URL ile açıkça verilen proje korunur.
- Sidebar boş metni **Sohbet yok**. Yakın zamanlılar başlığı listeyi kapatır ve ok sağa döner. Üç nokta menüsü gruplama, sıralama ve yeni bölüm sunar. Bilgi kartları yaklaşık 550 ms bekleme sonrası açılır.
- Mesaj gönderilince ortam özeti varsayılan olarak açılır. Başlıktaki düğme elle açıp kapatır. Sağ workspace açılması özeti zorla kalıcı kapatmamalıdır.
- Sohbet ve özet aynı `.conversation-group` içinde bulunur. Bu grubun genişliği 850 px altına düşünce özet otomatik gizlenir, boşluğu sohbet alır; genişleyince kullanıcının açık tercihi geri görünür. Sadece pencere genişliğini ölçmek yeterli değildir. Ek dar alan kuralı 900 px sınırındadır.
- Split sürüklemesi başlangıç konumu ve başlangıç oranından hesaplanır. Özet açıkken workspace genişliği kilitlenmemelidir. Grup oranı %20–75 aralığındadır.
- Başlık eylemleri: özet, alt terminal, sağ workspace. Sağ panel önce özellik seçiciyi gösterir; açılan özellikler sekmelerde çalışır. Artifacts sekmesi ürün dilinde **İncele** olarak sunulur.
- Terminal panelini gizlemek veya sekme değiştirmek oturumu öldürmez. Sekmeyi kapatmak yalnız o oturumu sonlandırır. Alt terminal bağımsız sekmelidir.
- Her iki terminalde sekme adı kayıtlı proje adından gelir; bu canlı shell çalışma dizini değildir. Uzun ad kısalır, tooltip tam ad gösterir.
- Terminalde varsayılan teknik PTY notu ve eski arama/Interrupt/Close araç çubuğu görünmez. Arama Ctrl+Shift+F ile açılır, Escape ile kapanır. Gerçek hatalar görünür kalır.
- İncele boşken tek sade boş durum gösterir. Yetkinlik kapalıysa **Çıktılara erişilemiyor**, ayrıntılar kapalı teknik detay alanında sunulur. Veri varsa mevcut governed artifact işlevleri korunur.
- Çalışma süresi, açılır işlem adımları ve küçük animasyonlar gerçek runtime olaylarına dayanır. Gizli model düşüncesi veya sahte işlem üretilmez. Reduced-motion desteklenir.
- Model seçimi gerçekten keşfedilmiş modellere bağlıdır. Normal effort mavi, Ultra mor degrade olabilir; referanstaki model adını sahte seçenek olarak eklemeyin.

## Kod haritası

Tüm frontend yolları `apps/operator-panel/src/` altındadır:

| Dosya / alan | Sorumluluk |
|---|---|
| `product-shell/pages/TaskPage.tsx` | Sohbet, özet, split, workspace ve oturum koordinasyonu |
| `product-shell/shell/TopBar.tsx`, `TaskMenu.tsx` | Sohbet başlığı, panel düğmeleri, görev menüsü |
| `product-shell/shell/Sidebar*.tsx` | Listeler, hover bilgi kartları, menüler |
| `product-shell/shell/ComposerProjectPicker.tsx` | Yeni sohbet proje seçimi |
| `product-shell/conversation/` | Mesaj sunumu, TurnActivity, gerçek çıktı kartları |
| `product-shell/workspace/WorkspaceTabs.tsx` | Sekmeler ve özellik seçici |
| `product-shell/workspace/ProductArtifactWorkspace.tsx` | Kompakt İncele yüzeyi ve artifact bağlantısı |
| `product-shell/bottom-dock/TerminalDock.tsx` | Alt terminal sekmeleri / boyutlandırma |
| `product-shell/terminal/TerminalSurface.tsx` | Xterm ve gerçek Tauri PTY yaşam döngüsü |
| `product-shell/browser/BrowserSurface.tsx` | Tarayıcı araç çubuğu ve native görünürlük |
| `components/assistant/AssistantQuickModelSettings.tsx` | Kompakt model/effort kontrolü |
| `assistant/useAssistantRuntimeSession.ts` | Runtime olayları ve gönderim başarısızlığı |

Backend görev başlığı güncellemesi: `imperaos/product_workspace/service.py`, `imperaos/artifacts/rpc_server.py` ve frontend `productWorkspaceClient.ts`. Başlık kırpılır, boş olamaz ve 240 karakterle sınırlıdır.

## Tekrarlanmaması gereken hatalar

1. AppShell alt Routes dışında olduğu için TopBar içinde `useParams()` görev kimliğini vermiyordu. `useMatch('/task/:taskId/*')` kullanılıyor. İzole bileşen testi bu bozukluğu yakalamaz; gerçek kabuğu açın.
2. React StrictMode state updater'ını tekrar çağırabilir. Yeni sekme kimliğini updater içinde üretmeyin; önce üretip sonra state'e ekleyin.
3. Ortam kartını gizlemek için yalnız viewport media query kullanmayın. Kullanıcı workspace'i büyütürken pencere aynı genişlikte kalır. Container query ve sohbet grubunun alanı esas alınır.
4. Gizlenen terminal bileşenini unmount etmek PTY'yi kapatır. Mount korunur; görünürlük/active ayrı iletilir. Native browser görünürlüğünü de doğru iletin.
5. PowerShell RGB ANSI yazı rengi xterm palette ayarını aşar. DOM renderer için `.xterm-rows span:not(.xterm-cursor)` beyaz renk kuralı var. Renderer değişirse yeniden kontrol edin.
6. Gönderim başarısızlığı false olarak üst katmana taşınmalı; taslak silinmemeli, tekrar deneme kullanıcı mesajını ikinci kez kaydetmemeli.
7. Vite watcher `src-tauri` build dosyalarını izlememeli; Windows kilitli DLL sorununa yol açar.

## Gerçek durum ve sınırlar

- Yeniden adlandırma, sabitleme, arşivleme, başlık/sohbet kopyalama ve aynı projede yeni sohbet bağlıdır. Paylaşım bağlantısı, yan sohbet, ayrı kopya, zamanlama ve yeni native pencere referanstaki tüm kapsamıyla henüz tamamlanmadı. Çalışmayan dekoratif düğme eklemeyin.
- Git satır ekleme/silme istatistikleri ve geri alma motor desteği yoktur. Çıktı sayısını git değişiklik sayısı olarak sunmayın.
- Kalıcı mesajlar saklanır; ayrıntılı runtime timeline ve elapsed metadata yeniden başlatma sonrası aynı kapsamda saklanmaz. Aynı metne sahip yanıtların activity eşleşmesi ayrıca gözden geçirilebilir.
- Terminal sekmeleri uygulama yeniden başlatıldığında aynı PTY'yi kurtarmaz.
- Artifact yetkinliği yapılandırmayla kapalı olabilir. Tasarım düzeltmesi bu yetkinliği açmaz.
- Referansın Tam erişim yazısı uğruna güvenlik politikasını gevşetmeyin. Debug yerel varsayılanları ile explicit enterprise / packaged fail-closed sınırları ayrıdır.
- Bu makinedeki provider durumu başka makineye taşınmış sayılmaz. Gerçek kodlama modeli çalıştırıldığı doğrulanmadı; model kurulumunu ve kimlik bilgilerini yeni ortamda kontrol edin.

## Başka bilgisayarda başlangıç ve doğrulama

README Quickstart ve Operator Panel kurulumunu izleyin; lockfile sürümlerini kullanın. Python ortamı, Node/pnpm, Rust ve platformun Tauri bağımlılıkları gerekir. Kullanıcıya ait mutlak yolları, geçici clipboard dosyalarını, model anahtarlarını veya yerel state'i repo içine taşımayın.

Panel dizininde `pnpm dev` web geliştirme sunucusunu, `pnpm tauri:dev` native geliştirmeyi başlatır. Mevcut Vite çalışırken ikinci sunucuyu açmayın; gerekirse geçici Tauri config ile beforeDevCommand boş bırakılır. Bu makinede `localhost:5173` çalışıyordu; IPv4 adresinin aynı listener olduğunu varsaymayın.

İlgili doğrulamalar:

```text
# apps/operator-panel içinde
pnpm test
pnpm build
pnpm lint
pnpm exec playwright test e2e/task-shell-layout.spec.ts

# depo kökünde
uv run pytest tests/test_product_workspace.py -q
cargo test --manifest-path apps/operator-panel/src-tauri/Cargo.toml --lib
```

Playwright yapılandırmasını okuyun: varsayılan yapılandırma build/preview başlatabilir. Geliştirme sunucusu kullanılıyorsa yerel geçici config oluşturup sadece o dosyayı kaldırın. `task-shell-layout.spec.ts`, `sidebar-layout.spec.ts` ve `product-model-settings.spec.ts` önemli regresyon akışlarıdır.

Görsel kontrolde gerçek kabuğu 1920 px, 1400 px ve workspace sürüklenerek daraltılmış sohbet alanında açın. Ortam kartının gizlenip geri gelmesini, composer merkezlenmesini, tüm panellerin birlikte taşmamasını, sekme adlarını, terminal rengini ve İncele boş/hata durumlarını kontrol edin. Mock browser testi native PTY veya gerçek model entegrasyonu kanıtı değildir. Sonuçları tarih ve gerçek test kapsamıyla kaydedin.

## 6 Eylül 2026 — UI durumları ve ayar kullanılabilirliği

- Product Shell tarayıcıda açıldığında kalıcı, kompakt bir önizleme/bağlantı açıklaması gösterir. Geliştirme köprüsünün örnek onay, ajan ve model kayıtları canlı masaüstü verisi sayılmaz; native uygulamada önizleme şeridi gösterilmez.
- Composer `disabledReason` kabul eder. Yeni görev ekranı proje yükleniyor, bağlantı başarısız ve proje seçimi hatası durumlarını gerçek yanıt işleme durumundan ayırır.
- Ayar araması bölüm başlıklarının yanında alan adlarını da tarar. “model” sorgusu Asistan ve AI Sağlayıcıları bölümlerini bulur; eşleşme yoksa açık sonuç mesajı gösterilir.
- AI Sağlayıcıları bölümü mevcut model keşif servisine bağlıdır. Kullanılamayan modeller devre dışıdır; keşif başarısız olduğunda kayıtlı seçim korunur. Yerel Transformers seçimi HF model alanına kaydedilir. Kurulum bağlantısı ve yeniden keşif eylemi sunulur; kimlik bilgileri otomatik kurulmaz.
- Ayarlar ve koleksiyonların kullanıcı metinleri `product-shell/ui/productCopy.ts` üzerinden Türkçe/İngilizce sunulur. Sistem ayarlarına geçiş korunur; teknik kimlikler ve runtime kodları veri olarak kalır. Bu çalışma bütün eski panelin çeviri kapsamını tamamladığı anlamına gelmez.
- Koleksiyonlarda yükleme durumu, anlaşılır hata ve kapalı teknik ayrıntılar vardır. Kütüphane yenilemesi seçili çıktının ayrıntısını da tekrar yükler; yalnız listeyi yenilemek kurtarma için yeterli değildir.
- Ajan listesi kompakt satırlar kullanır; ayrıntıda hazırlık ve kanıt bilgileri korunur. Eski kartın `::before` gradyanı ürün CSS katmanında kapatılır. Frozen UI Lab dosyaları değiştirilmez.
- Zamanlananlar mevcut sürümde desteklenmiyor olarak açıkça belirtilir; elle yeni görev başlatma bağlantısı sunulur. Otomasyon motoru eklenmemiştir.

Doğrulama: 144 Vitest dosyasında 601 test geçti; `pnpm build`, `pnpm lint` ve `git diff --check` başarılı. Bu makinede testler Node 24 ile `NODE_OPTIONS=--no-experimental-webstorage` kullanılarak çalıştırıldı; Node 26 global depolama davranışı test ortamıyla uyumlu değildi. Derleme büyük chunk uyarısı veriyor; paket bölme bu değişikliğin kapsamı dışında.

Görsel kontrol gerçek AppShell üzerinden Chrome'da ana ekran, ayar araması/model seçimi, ajanlar, kütüphane hata durumu ve Zamanlananlar için yapıldı. Ayarlar 1200 ve 1000 px, ajanlar 1200 px genişlikte ayrıca incelendi; geçici viewport sıfırlandı. Native uygulama başlatıldı, ancak canlı provider çağrısı, PTY ve dolu sohbet + workspace + alt terminal birleşimi bu turda görsel olarak yeniden doğrulanmadı.

## 6 Eylül 2026 — Native doğrulama ve model keşfi düzeltmesi

Debug macOS `.app` paketi derlendi ve gerçek Tauri AppShell üzerinde kontrol edildi. Mevcut proje ve sohbet açıldı; yeni model mesajı gönderilmedi. Test için açılan gerçek zsh PTY, `__IMPERAOS_NATIVE_PTY_OK__` işaretini yazdırdı. Alt panel gizlenip yeniden açıldığında çıktı korundu. Sohbet, workspace ve alt terminal birlikte açıkken özet alanı daralan sohbet genişliğinde gizlendi; workspace kapatılınca geri geldi. Test terminali kontrol sonunda kapatıldı. Native uygulamada tarayıcı önizleme şeridi gösterilmedi. Bu kontroller önceki bölümdeki native PTY ve birleşik panel doğrulama boşluğunu kapatır.

Model keşfinde yapılandırılmış bir HF model adının, Transformers kurulu olmasa bile sağlayıcıyı kullanılabilir göstermesi düzeltildi. Keşif artık `transformers` ve `torch` bağımlılıklarının varlığını denetler; eksik bağımlılığı açık hata koduyla bildirir. Model ağırlıkları indirilmez ve önbellek kontrol edilmiş sayılmaz. Bu makinede assistant doctor artık `setup_required`, native model ayarları “Kullanılabilir model bulunamadı” gösteriyor. Canlı model yanıtı hâlâ doğrulanmadı; kullanılabilir sağlayıcı kurulumu gerekir.

Doğrulama: `tests/test_operator_provider_models.py`, `tests/test_assistant_cli.py` ve `tests/test_assistant_real_runtime_gate.py` içindeki 14 Python testi geçti. Değişen Python dosyaları Ruff kontrolünden geçti. Rust `terminal::tests` kapsamındaki 5 test, gerçek PTY uçtan uca testi dahil, geçti. Debug Tauri uygulama paketi başarıyla derlendi. Bağımlılık keşfi, modelin ağırlıklarının mevcut olduğunu veya çıkarımın başarılı olacağını kanıtlamaz.


## 6 Eylül 2026 — macOS cam sidebar ve bütünleşik başlık

Kullanıcının yeni referansı sidebar için masaüstü renklerini geçiren gerçek bulanıklık ve uygulama yüzeyiyle birleşen başlık gerektirir. macOS platform yapılandırması `Overlay`, gizli pencere başlığı ve native `sidebar` efekti kullanır. Sistem pencere düğmeleri korunur; sidebar araç satırı ve kapalı sidebar üst başlığı düğmeler için 96 px ayırır. Boş başlık alanlarından pencere sürüklenebilir.

Native NSVisualEffectView masaüstünü gerçekten bulanıklaştırır; üstündeki saydam mavi/yeşil renk katmanı referansın tonlarını korur. Yalnız native macOS Product Shell kökleri saydamdır; sohbet/workspace yüzeyleri opak kalır. Native materyal uygulamanın açık/koyu temasıyla eşleştirilir. Web ve diğer platformlar mevcut opak yüzeyi korur. Frozen UI Lab dosyaları değiştirilmez.

Tauri macOS saydam webview için `macos-private-api` özelliğini gerektirir; bu dağıtım yöntemi Mac App Store kabul koşullarıyla uyumlu değildir. İleride App Store hedeflenirse native pencere yaklaşımı yeniden değerlendirilmelidir. Sistem saydamlığı azaltma tercihi ve masaüstü arka planı camın görünümünü etkiler.

Doğrulama: macOS debug `.app` paketi yeniden derlenip açıldı. Native ana ekran, sohbet başlığı ve sidebar kapalı durumu görsel olarak kontrol edildi; ayrı standart başlık şeridi kaldırıldı, pencere düğmeleri için boşluk korundu. Tema senkronizasyonu/temizliği ve mevcut sidebar/başlık sözleşmeleri dahil 4 Vitest dosyasında 23 test geçti; frontend build, ESLint ve `git diff --check` başarılı. Sistem düzeyindeki saydamlığı azaltma tercihi değiştirilmedi; Windows/Linux native görünümü bu makinede çalıştırılmadı.
