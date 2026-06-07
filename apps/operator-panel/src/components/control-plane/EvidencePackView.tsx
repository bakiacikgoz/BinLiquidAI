import { formatReasonCode, formatReasonCodeList } from '../../control-plane/reasonCodes';
import type { EvidencePackSummary, PilotLaunchReadinessStatus, PilotLaunchStatusTile } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';
import { ReasonChip, StatusBadge } from '../primitives/Token';

type EvidencePackViewProps = {
  evidencePacks: EvidencePackSummary[];
  verifyResult: unknown;
  verifyDisabledReason?: string;
  pilotLaunch?: PilotLaunchReadinessStatus | null;
  locale?: UiLocale;
  onVerify: () => void;
};

const copy = {
  en: {
    evidencePacks: 'Evidence packs',
    noEvidencePack: 'No evidence pack is available from the current snapshot.',
    verifyLatest: 'Verify latest',
    packs: 'Packs',
    noRunLinked: 'no run linked',
    signature: 'Signature',
    missing: 'missing',
    enterpriseEvidence: 'enterprise evidence',
    replay: 'Replay',
    notAvailable: 'not_available',
    integrityProof: 'integrity proof',
    selectedPack: 'Selected pack',
    exportPath: 'Export path',
    artifacts: 'Artifacts',
    hashChain: 'Hash chain',
    claimGuard: 'Claim guard',
    redaction: 'Redaction',
    verificationResult: 'Verification result',
    status: 'Status',
    artifact: 'Artifact',
    blockers: 'Blockers',
    pending: 'pending',
    blocked: 'blocked',
    unknown: 'unknown',
    notRun: 'not run',
    passed: 'passed',
    failed: 'failed',
    packBlocker: 'pack blocker',
    requiredBeforeReadyClaim: 'required before ready claim',
    enterpriseHatA: 'Enterprise Hat A',
    evidenceCorpus: 'Evidence corpus',
  },
  tr: {
    evidencePacks: 'Kanıt paketleri',
    noEvidencePack: 'Geçerli snapshot içinde evidence pack yok.',
    verifyLatest: 'Sonuncuyu doğrula',
    packs: 'Packler',
    noRunLinked: 'bağlı run yok',
    signature: 'İmza',
    missing: 'eksik',
    enterpriseEvidence: 'kurumsal kanıt',
    replay: 'Replay',
    notAvailable: 'kullanılamıyor',
    integrityProof: 'bütünlük kanıtı',
    selectedPack: 'Seçili pack',
    exportPath: 'Dışa aktarım yolu',
    artifacts: 'Artefaktlar',
    hashChain: 'Hash zinciri',
    claimGuard: 'Claim koruması',
    redaction: 'Redaksiyon',
    verificationResult: 'Doğrulama sonucu',
    status: 'Durum',
    artifact: 'Artefakt',
    blockers: 'Blockerlar',
    pending: 'bekliyor',
    blocked: 'bloke',
    unknown: 'bilinmiyor',
    notRun: 'çalışmadı',
    passed: 'geçti',
    failed: 'başarısız',
    packBlocker: 'pack blocker',
    requiredBeforeReadyClaim: 'ready claim öncesi gerekli',
    enterpriseHatA: 'Enterprise Hat A',
    evidenceCorpus: 'Kanıt derlemi',
  },
} satisfies Record<UiLocale, Record<string, string>>;

export function EvidencePackView({
  evidencePacks,
  verifyResult,
  verifyDisabledReason = '',
  pilotLaunch,
  locale = 'en',
  onVerify,
}: EvidencePackViewProps) {
  const text = copy[locale];
  const selectedPack = evidencePacks[0] ?? null;
  const verification = asRecord(verifyResult);
  const blockingReasons = selectedPack?.blockingReasons ?? [
    'QUALIFICATION_REPORT_MISSING',
    'SIGNED_PLATFORM_QUALIFICATION_MISSING',
  ];
  const verificationStatus = translateValue(readString(verification, 'status', readString(verification, 'code', 'not run')), text);
  const verificationBlockingReasons = readArray(verification, 'blocking_reasons');

  return (
    <article className="page-card evidence-pack-view">
      <div className="page-card-header">
        <div>
          <h3>{text.evidencePacks}</h3>
          <p className="supporting">
            {selectedPack ? selectedPack.packId : text.noEvidencePack}
          </p>
        </div>
        <button
          className="ghost-btn"
          type="button"
          disabled={Boolean(verifyDisabledReason)}
          title={verifyDisabledReason || undefined}
          onClick={onVerify}
        >
          {text.verifyLatest}
        </button>
      </div>
      {verifyDisabledReason ? <p className="warning-inline">{verifyDisabledReason}</p> : null}

      <div className="metric-grid compact-metric-grid">
        <article className="metric-card">
          <h3>{text.packs}</h3>
          <p className="metric">{evidencePacks.length}</p>
          <small>{selectedPack?.runId ?? text.noRunLinked}</small>
        </article>
        <article className="metric-card">
          <h3>{text.signature}</h3>
          <p className="metric">{translateValue(selectedPack?.signatureStatus ?? 'missing', text)}</p>
          <small>{text.enterpriseEvidence}</small>
        </article>
        <article className="metric-card">
          <h3>{text.replay}</h3>
          <p className="metric">{translateValue(selectedPack?.replayStatus ?? 'not_available', text)}</p>
          <small>{text.integrityProof}</small>
        </article>
      </div>

      <div className="section-grid two-up">
        <article className="inner-card">
          <h3>{text.selectedPack}</h3>
          <div className="metric-list">
            <MetricRow label={text.exportPath} value={selectedPack?.exportPath ?? text.missing} />
            <MetricRow label={text.artifacts} value={String(selectedPack?.artifactCount ?? 0)} />
            <MetricRow label={text.hashChain} value={translateValue(selectedPack?.hashChainStatus ?? 'pending', text)} />
            <MetricRow label={text.claimGuard} value={translateValue(selectedPack?.claimGuardStatus ?? 'blocked', text)} />
            <MetricRow label={text.redaction} value={translateValue(selectedPack?.redactionStatus ?? 'unknown', text)} />
          </div>
        </article>
        <article className="inner-card">
          <h3>{text.verificationResult}</h3>
          <div className="metric-list">
            <MetricRow label={text.status} value={verificationStatus} />
            <MetricRow label={text.hashChain} value={readBoolLabel(verification, 'hash_chain_verified', text)} />
            <MetricRow label={text.signature} value={readBoolLabel(verification, 'signature_verified', text)} />
            <MetricRow label={text.replay} value={readBoolLabel(verification, 'replay_verified', text)} />
          </div>
          {verificationBlockingReasons.length > 0 ? (
            <p className="warning-inline">{formatReasonCodeList(verificationBlockingReasons, locale)}</p>
          ) : null}
        </article>
      </div>

      <div className="section-grid two-up">
        <PilotEvidenceTile tile={pilotLaunch?.enterpriseHatA} fallbackLabel={text.enterpriseHatA} text={text} />
        <PilotEvidenceTile tile={pilotLaunch?.evidenceCorpus} fallbackLabel={text.evidenceCorpus} text={text} />
      </div>

      <div className="run-list">
        {blockingReasons.map((reason) => (
          <article className="run-list-item" key={reason}>
            <div className="run-list-main">
              <strong>{formatReasonCode(reason, locale)}</strong>
              <div className="run-list-meta">
                <ReasonChip title={reason}>{reason}</ReasonChip>
              </div>
            </div>
            <StatusBadge tone={selectedPack ? 'warning' : 'error'}>
              {selectedPack ? text.packBlocker : text.requiredBeforeReadyClaim}
            </StatusBadge>
          </article>
        ))}
      </div>
    </article>
  );
}

function PilotEvidenceTile({
  tile,
  fallbackLabel,
  text,
}: {
  tile?: PilotLaunchStatusTile | null;
  fallbackLabel: string;
  text: (typeof copy)['en'];
}) {
  return (
    <article className="inner-card">
      <h3>{tile?.label ?? fallbackLabel}</h3>
      <div className="metric-list">
        <MetricRow label={text.status} value={translateValue(tile?.status ?? 'unknown', text)} />
        <MetricRow label={text.artifact} value={tile?.path ?? text.missing} />
        <MetricRow label={text.blockers} value={String(tile?.blockingReasons.length ?? 0)} />
      </div>
    </article>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readArray(source: Record<string, unknown>, key: string): string[] {
  const value = source[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function readBoolLabel(source: Record<string, unknown>, key: string, text: (typeof copy)['en']): string {
  if (!(key in source)) {
    return text.notRun;
  }
  return source[key] === true ? text.passed : text.failed;
}

function translateValue(value: string, text: (typeof copy)['en']): string {
  return text[value as keyof typeof text] ?? value;
}
