import type { UiLocale } from '../i18n';

export const reasonCodeMessages: Record<UiLocale, Record<string, string>> = {
  en: {
    CLEAN_MACHINE_SMOKE_MISSING: 'Clean-machine desktop smoke evidence is missing.',
    COMPUTER_USE_CLAIM_BLOCKED: 'Computer-use remains blocked until qualification evidence exists.',
    COMPUTER_USE_EVIDENCE_MISSING: 'Computer-use qualification evidence is missing.',
    CONFIRMATION_REQUIRED: 'This operation requires an explicit operator confirmation.',
    DATA_SOURCE_PREVIEW_FIXTURE: 'This view is using explicit preview fixture data.',
    DESTRUCTIVE_OPERATION_DISABLED: 'Destructive execution is disabled for the pilot UI.',
    EVIDENCE_HASH_MISMATCH: 'Evidence pack hash chain verification failed.',
    HAT_B_EVIDENCE_MISSING: 'Hat B desktop release evidence is missing.',
    IDENTITY_INVALID: 'The operator identity assertion is invalid or unavailable.',
    IDENTITY_UNVERIFIED: 'The operator identity has not been verified.',
    INTEGRITY_VERIFY_FAILED: 'Evidence manifest integrity verification failed.',
    LINUX_COMPUTER_USE_NOT_QUALIFIED: 'Linux live computer-use is not qualified.',
    MACOS_LIVE_DISABLED: 'macOS live computer-use is disabled by claim guard.',
    MACOS_NOTARIZATION_EVIDENCE_MISSING: 'macOS notarization evidence is missing.',
    MULTI_TENANT_CLOUD_OUT_OF_SCOPE: 'Cloud multi-tenant operation is outside this pilot scope.',
    NO_EVIDENCE_PACKS: 'No evidence pack is available to verify.',
    NO_PENDING_APPROVALS: 'No pending approval is available for review.',
    POLICY_FILE_MISSING: 'The active policy file is missing.',
    QUALIFICATION_MISSING: 'Qualification evidence has not been generated.',
    QUALIFICATION_REPORT_MISSING: 'The enterprise qualification report is missing.',
    REPLAY_VERIFY_FAILED: 'Evidence replay verification failed.',
    REQUIRED_ARTIFACT_MISSING: 'A required evidence artifact is missing from the pack.',
    RESTORE_TARGET_REQUIRED: 'Select a restore target before running this preflight.',
    SIGNATURE_VERIFICATION_FAILED: 'Evidence signature verification failed.',
    SIGNED_PLATFORM_QUALIFICATION_MISSING: 'Signed platform qualification evidence is missing.',
    SILENT_MOCK_FALLBACK: 'Live mode fell back to mock data and must fail closed.',
    TEAM_RUNTIME_DISABLED: 'Team runtime is disabled in this configuration.',
    WINDOWS_COMPUTER_USE_NOT_QUALIFIED: 'Windows live computer-use is not qualified.',
    WINDOWS_SIGNED_RC_EVIDENCE_MISSING: 'Windows signed release-candidate evidence is missing.',
  },
  tr: {
    CLEAN_MACHINE_SMOKE_MISSING: 'Temiz makine desktop smoke kanıtı eksik.',
    COMPUTER_USE_CLAIM_BLOCKED: 'Computer-use, qualification kanıtı oluşana kadar bloke kalır.',
    COMPUTER_USE_EVIDENCE_MISSING: 'Computer-use qualification kanıtı eksik.',
    CONFIRMATION_REQUIRED: 'Bu operasyon açık operatör onayı gerektirir.',
    DATA_SOURCE_PREVIEW_FIXTURE: 'Bu görünüm açık preview fixture verisi kullanıyor.',
    DESTRUCTIVE_OPERATION_DISABLED: 'Yıkıcı yürütme pilot UI için kapalıdır.',
    EVIDENCE_HASH_MISMATCH: 'Evidence pack hash zinciri doğrulaması başarısız.',
    HAT_B_EVIDENCE_MISSING: 'Hat B desktop release kanıtı eksik.',
    IDENTITY_INVALID: 'Operatör kimlik beyanı geçersiz veya erişilemiyor.',
    IDENTITY_UNVERIFIED: 'Operatör kimliği doğrulanmadı.',
    INTEGRITY_VERIFY_FAILED: 'Evidence manifest bütünlük doğrulaması başarısız.',
    LINUX_COMPUTER_USE_NOT_QUALIFIED: 'Linux canlı computer-use qualified değil.',
    MACOS_LIVE_DISABLED: 'macOS canlı computer-use claim guard tarafından kapalı.',
    MACOS_NOTARIZATION_EVIDENCE_MISSING: 'macOS notarization kanıtı eksik.',
    MULTI_TENANT_CLOUD_OUT_OF_SCOPE: 'Cloud multi-tenant çalışma bu pilot kapsamının dışında.',
    NO_EVIDENCE_PACKS: 'Doğrulanabilir evidence pack yok.',
    NO_PENDING_APPROVALS: 'İncelenecek bekleyen onay yok.',
    POLICY_FILE_MISSING: 'Aktif policy dosyası eksik.',
    QUALIFICATION_MISSING: 'Qualification kanıtı henüz üretilmedi.',
    QUALIFICATION_REPORT_MISSING: 'Enterprise qualification raporu eksik.',
    REPLAY_VERIFY_FAILED: 'Evidence replay doğrulaması başarısız.',
    REQUIRED_ARTIFACT_MISSING: 'Evidence pack içinde zorunlu bir artifact eksik.',
    RESTORE_TARGET_REQUIRED: 'Bu preflight için önce restore hedefi seçin.',
    SIGNATURE_VERIFICATION_FAILED: 'Evidence imza doğrulaması başarısız.',
    SIGNED_PLATFORM_QUALIFICATION_MISSING: 'İmzalı platform qualification kanıtı eksik.',
    SILENT_MOCK_FALLBACK: 'Canlı mod mock veriye düştü ve fail-closed olmalı.',
    TEAM_RUNTIME_DISABLED: 'Team runtime bu yapılandırmada kapalı.',
    WINDOWS_COMPUTER_USE_NOT_QUALIFIED: 'Windows canlı computer-use qualified değil.',
    WINDOWS_SIGNED_RC_EVIDENCE_MISSING: 'Windows imzalı release-candidate kanıtı eksik.',
  },
};

export function getReasonCodeMessage(code: string | null | undefined, locale: UiLocale): string {
  if (!code) {
    return '';
  }
  return reasonCodeMessages[locale][code] ?? humanizeReasonCode(code);
}

export function formatReasonCode(code: string | null | undefined, locale: UiLocale): string {
  if (!code) {
    return '';
  }
  return `${code}: ${getReasonCodeMessage(code, locale)}`;
}

export function formatReasonCodeList(codes: Array<string | null | undefined>, locale: UiLocale): string {
  return codes.filter((code): code is string => Boolean(code)).map((code) => formatReasonCode(code, locale)).join(' | ');
}

function humanizeReasonCode(code: string): string {
  return code
    .toLowerCase()
    .split('_')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}
