# Arayüz ve kullanılabilirlik denetimi — 5 Eylül 2026

## Düzeltilen sorunlar

- Model ayarlarının saydam, başlıksız ve kapanma davranışı eksik yüzeyi: opak tema yüzeyi, okunabilir alanlar, Türkçe etiketler, başlık/açıklama, kapat düğmesi, Escape ve dışarı tıklama, tetikleyiciye klavye odağı dönüşü.
- Ayarlar panelinin dar/kısa pencerelerde ekran dışına taşması: pencereye göre konum ve kaydırılabilir yükseklik.
- Ana sayfa hatasının gönderme/model düğmelerini örtmesi: hata mesajı normal içerik akışında, yeniden deneme ve teknik ayrıntılar ayrı.
- Açık temada öneri kartlarının koyu zemin üzerinde okunamayan metni.
- Başarısız gönderimde taslağın silinmesi, bekleyen isteğin çift gönderilmesi ve yeni seçilen taslağın eski isteğin sonunda silinmesi.
- Hem eski oturum hem AI SDK oturumunda motor başlangıç hatasının başarı gibi dönmesi.
- Başlangıcı başarısız mesajın yeniden denemede ikinci kez kaydedilmesi.
- React StrictMode altında görev projesinin sürekli yükleniyor kalması.
- Yalnızca ilk proje sayfasının alınması ve seçili projenin sessizce başka projeye dönüşmesi.
- Projeler yüklenmeden görev açılması; bağlantı hatasından sonra yeniden deneme olmaması.
- Görev ayarı ve mesaj kaydı hatalarında geri bildirim eksikliği.
- Hızlı seçimde eski onay/artifact ayrıntılarının yeni seçimi ezmesi; kanıt yüklenmeden onay eylemi sunulması.
- Son çalışma sekmesinin kapatılınca yeniden oluşması.
- Yanlış menü adları ve sabit sahte kullanıcı kimliği.
- Kaynak ortamında çekirdek komutunun PATH üzerinde bulunamaması: debug derlemesi güvenilir derleme deposunun kurulu sanal ortamını kullanır.
- Windows Rust derleme çıktıları kilitlendiğinde Vite dosya izleyicisinin çökmesi.

## Doğrulama

- Hata regresyonları önce başarısız, ardından başarılı çalıştırıldı.
- Ürün kabuğu, model seçimi, gönderme ve oturum testleri; TypeScript ve hedefli ESLint kontrolü.
- Üretim Vite derlemesi başarılı (mevcut büyük paket uyarıları devam ediyor).
- Rust kütüphanesinde 71 test başarılı; gerçek kurulu çekirdek, temizlenmiş köprü ortamından başlatıldı.
- Tarayıcıda 1280x800, 900x600, 480x640 ve 375x667 panel sınırları kontrol edildi; yatay taşma yok.
- Üç Playwright regresyonu: opak yüzey, ekran sınırları, Escape/odak dönüşü ve dışarı tıklama.
- Masaüstü uygulaması yeniden başlatıldı; ImperaOS penceresi açık.

## Ürün sınırları ve kalan kurulum ihtiyacı

Bu çalışma bütün olası ürün hatalarının giderildiği iddiası değildir. Otomasyon yeteneği bu runtime için kayıtlı değil; kütüphane ve ajan sayfalarının kapsamı mevcut kayıtları incelemektir. Bu sayfaların etiketleri gerçek yetenekleri yansıtacak şekilde düzeltildi.

Gerçek çekirdek model sorgusunda Ollama kurulu değil; uzak sağlayıcılar kapalı. Yerel Transformers için yapılandırılan varsayılan distilgpt2. Model keşfi tek başına kaliteli bir kodlama asistanının çalıştığını kanıtlamaz; uygun model kurulumu/sağlayıcı yapılandırması ve gerçek görev yürütme denemesi ayrıca gerekir. Bu denetimde ücretli sağlayıcı açılmadı veya model indirilmedi.

## Referans tasarım ve sohbet başlatma düzeltmesi

- Model seçimi 304px genişlikte, seçili öğe işaretli kompakt listeye dönüştürüldü. Gerçek model keşif verisi kullanılır; desteklenmeyen modeller kullanılabilir gibi gösterilmez.
- Düşünme düzeyi dört kademeli kaydırıcıya alındı; ayrıntılı sağlayıcı, hız ve onay ayarları gelişmiş bölümde tutuldu.
- Proje yükleme sorunu sağ üstte nötr yüzeyli, küçültülebilen/yeniden açılabilen ve yeniden deneme sunan bildirime taşındı.
- Görevler ve her proje için görünür Yeni sohbet eylemi eklendi. Proje satırı yalnızca sohbet listesini açıp kapatır. Yeni klasör kaydı ilgili projenin sohbet oluşturma ekranını açar.
- Asıl çalışma alanı engeli: kaynak masaüstü derlemesi açık host profili olmadan enterprise kimliği arıyordu; RPC başlamadan reddediliyordu. Debug derlemesi, host profili belirtilmediyse mevcut balanced yerel politikasını kullanır. Açık enterprise ayarı ve paketli derlemenin güvenlik davranışı korunur.
- Gerçek Python supervisor ile izole geçici depoda proje/görev oluşturma ve listeleme doğrulandı. 74 Rust testi, 144 arayüz testi ve üç panel yerleşim tarayıcı testi başarılı.
- Son incelemede yapılandırılmış/yerelde kurulu olmayan kullanılabilir modellerin seçilebilmesi ve ilk mesajın kaydı başarısız olduğunda aynı sohbet kaydının yeniden kullanılması için ek regresyonlar eklendi; odaklı testler başarılı.

## Sidebar yerleşimi ve bilgi kartları

- Proje başlığı, yeni sohbet ve satır eylemleri tek satırda tutuldu; boş proje altında girintili Sohbet yok durumu eklendi.
- Sidebar zemini nötr #202020; hover/seçim yüzeyleri #2b2b2b ve #303030 olarak düzenlendi.
- Proje ve sohbet satırlarında 550ms bekleyince kayıtlı proje/sohbet/klasör bilgilerini gösteren ekran sınırları içinde bilgi kartı eklendi. Klavye odağı da kartı açar, Escape/ayrılma kapatır.
- 12 Sidebar testi ve izole tarayıcı verisiyle yeni proje kaydından sonra satır yerleşimi/bilgi kartı testi başarılı. Bu tarayıcı testi gerçek kullanıcı verisini değiştirmez.
