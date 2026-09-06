import { loadSettings, resolveLocale } from '../../settings';
import type { UiLocale } from '../../i18n';

const tr: Record<string, string> = {
  'Account': 'Hesap', 'System': 'Sistem', 'General': 'Genel', 'Appearance': 'Görünüm',
  'Assistant': 'Asistan', 'AI providers': 'AI Sağlayıcıları', 'Security': 'Güvenlik', 'Shortcuts': 'Kısayollar',
  'Back to app': 'Uygulamaya dön', 'Search settings': 'Ayarlarda ara', 'Filter': 'Filtre',
  'Operator settings': 'Operatör ayarları', 'Manage your workspace preferences.': 'Çalışma alanı tercihlerinizi yönetin.',
  'Operator profile': 'Operatör profili', 'Operator identity': 'Operatör kimliği',
  'Identity used for approval decisions.': 'Onay kararlarında kullanılan operatör kimliği.',
  'Workspace': 'Çalışma alanı', 'Language': 'Dil', 'Preferred interface language.': 'Tercih edilen arayüz dili.',
  'Automatic': 'Otomatik', 'Advanced': 'Gelişmiş', 'Advanced system settings': 'Gelişmiş sistem ayarları',
  'Manage connection and security settings in the system panel.': 'Bağlantı ve güvenlik ayarlarını sistem panelinde yönetin.',
  'Open system settings': 'Sistem ayarlarını aç', 'Theme': 'Tema', 'Choose an interface theme.': 'Arayüz temasını seçin.',
  'Dark': 'Koyu', 'Light': 'Açık', 'Assistant profile': 'Asistan profili',
  'Default runtime profile for new tasks.': 'Yeni görevlerde kullanılacak çalışma profili.',
  'Model': 'Model', 'Choose a discovered model.': 'Keşfedilen modellerden birini seçin.',
  'Profile default': 'Profil varsayılanı', 'Unavailable': 'Kullanılamıyor', 'Loading models…': 'Modeller yükleniyor…',
  'Refresh models': 'Modelleri yenile', 'Models could not be loaded.': 'Modeller yüklenemedi.',
  'No available models found.': 'Kullanılabilir model bulunamadı.',
  'Configure a provider or start your local model service, then refresh.': 'Bir sağlayıcı yapılandırın veya yerel model servisinizi başlatın; ardından listeyi yenileyin.',
  'Configure providers': 'Sağlayıcıları yapılandır', 'Default approval profile': 'Varsayılan onay profili',
  'Approval behavior within the current policy.': 'Geçerli politika sınırları içindeki onay davranışı.',
  'Always ask': 'Her zaman onay iste', 'Risk-based approval': 'Riske göre onay iste', 'Automatic within policy': 'Politika içinde otomatik',
  'Global search': 'Genel arama', 'Search projects, tasks, outputs and approvals.': 'Proje, görev, çıktı ve onaylarda arayın.',
  'Terminal search': 'Terminalde arama', 'Search the focused terminal.': 'Odaklanılan terminal içinde arayın.',
  'Close search': 'Aramayı kapat', 'Dismiss the open search panel.': 'Açık arama panelini kapatın.',
  'Save settings': 'Ayarları kaydet', 'Settings saved.': 'Ayarlar kaydedildi.', 'No settings found.': 'Ayar bulunamadı.',
  'Refresh': 'Yenile', 'Technical details': 'Teknik ayrıntılar',
  'This view could not be loaded. Retry, or check the desktop connection.': 'Bu görünüm yüklenemedi. Yeniden deneyin veya masaüstü bağlantısını kontrol edin.',
  'Preview · Sample data may appear here. Use the desktop app for live workspace data and actions.': 'Önizleme · Burada örnek veriler görünebilir. Canlı çalışma alanı ve işlemler için masaüstü uygulamasını kullanın.',
  'Browser view · Open the desktop app to connect to your workspace.': 'Tarayıcı görünümü · Çalışma alanına bağlanmak için masaüstü uygulamasını açın.',
  'Library': 'Çalışma kütüphanesi', 'Your work, in one place.': 'Çalışmaların, tek yerde.',
  'Documents, spreadsheets and presentations from your tasks.': 'Görevlerde üretilen belgeler, tablolar ve sunumlar.',
  'No outputs in this workspace yet.': 'Bu çalışma alanında henüz çıktı yok.', 'No output selected': 'Çıktı seçilmedi',
  'Select an output to inspect its details.': 'Ayrıntılarını incelemek için bir çıktı seçin.',
  'Title': 'Başlık', 'Artifact ID': 'Çıktı kimliği', 'Kind': 'Tür', 'Status': 'Durum', 'Data class': 'Veri sınıfı',
  'Revision': 'Sürüm', 'Revision number': 'Sürüm numarası', 'Change summary': 'Değişiklik özeti', 'Updated': 'Güncellenme',
  'Approvals': 'Onaylar', 'Review actions that need your decision.': 'Kararınızı bekleyen işlemleri gözden geçirin.',
  'No pending approvals.': 'Bekleyen onay yok.', 'No approval selected': 'Onay seçilmedi',
  'Select an approval to inspect its details.': 'Ayrıntılarını incelemek için bir onay seçin.',
  'Execution': 'Yürütme', 'Run': 'Çalıştırma', 'Target kind': 'Hedef türü', 'Target': 'Hedef', 'Risk': 'Risk',
  'Category': 'Kategori', 'Requested by': 'Talep eden', 'Decision reason': 'Karar gerekçesi', 'Expires': 'Son geçerlilik', 'Policy hash': 'Politika özeti',
  'Approve': 'Onayla', 'Reject': 'Reddet', 'Set an operator identity in Settings before deciding.': 'Karar vermeden önce Ayarlar bölümünde operatör kimliğinizi belirtin.',
  'Agents': 'Ajanlar', 'Your team': 'Çalışan ekip', 'Registered agents and their status.': 'Kayıtlı ajanlar ve durumları.',
  'Scheduled tasks': 'Zamanlananlar', 'Not available yet': 'Henüz kullanılamıyor',
  'Scheduled tasks are not supported by this desktop version.': 'Bu masaüstü sürümü zamanlanmış görevleri henüz desteklemiyor.',
  'You can start a task manually. No schedule has been created.': 'Bir görevi elle başlatabilirsiniz. Herhangi bir zamanlama oluşturulmadı.',
  'New task': 'Yeni görev', 'Loading…': 'Yükleniyor…',
};

export function productText(locale: UiLocale = resolveLocale(loadSettings().locale)) {
  return (value: string) => locale === 'tr' ? (tr[value] ?? value) : value;
}

export function desktopConnected() {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}
