# ImperaOS arayüz tasarımı ve ajan devir rehberi

Bu belge 5 Eylül 2026 tarihindeki kullanıcı tercihlerini ve uygulama sırasında öğrenilenleri taşır. Başka bir bilgisayarda çalışmaya başlamadan önce bunu ve kökteki AGENTS.md dosyasını okuyun. Eski sohbet ekran görüntülerindeki başarı iddiaları test kanıtı değildir.

## Tasarım dili

Kullanıcı kompakt, sakin, Codex benzeri koyu bir masaüstü arayüzü istiyor. Büyük mavi kartlar, teknik durum rozetleri ve kalın araç çubukları uygun değil. Ürün adı ImperaOS olarak kalır.

| Alan | Kabul edilen ölçü / görünüm |
|---|---|
| Ana yüzey, terminal, workspace | `#181818` |
| Sidebar | `#202020`; hover `#2b2b2b`, seçili `#303030` |
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
