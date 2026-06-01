import { formatReasonCode, formatReasonCodeList } from '../../control-plane/reasonCodes';
import type { EvidencePackSummary } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';

type EvidencePackViewProps = {
  evidencePacks: EvidencePackSummary[];
  verifyResult: unknown;
  verifyDisabledReason?: string;
  locale?: UiLocale;
  onVerify: () => void;
};

export function EvidencePackView({
  evidencePacks,
  verifyResult,
  verifyDisabledReason = '',
  locale = 'en',
  onVerify,
}: EvidencePackViewProps) {
  const selectedPack = evidencePacks[0] ?? null;
  const verification = asRecord(verifyResult);
  const blockingReasons = selectedPack?.blockingReasons ?? [
    'QUALIFICATION_REPORT_MISSING',
    'SIGNED_PLATFORM_QUALIFICATION_MISSING',
  ];
  const verificationStatus = readString(verification, 'status', readString(verification, 'code', 'not run'));
  const verificationBlockingReasons = readArray(verification, 'blocking_reasons');

  return (
    <article className="page-card evidence-pack-view">
      <div className="page-card-header">
        <div>
          <h3>Evidence packs</h3>
          <p className="supporting">
            {selectedPack ? selectedPack.packId : 'No evidence pack is available from the current snapshot.'}
          </p>
        </div>
        <button
          className="ghost-btn"
          type="button"
          disabled={Boolean(verifyDisabledReason)}
          title={verifyDisabledReason || undefined}
          onClick={onVerify}
        >
          Verify latest
        </button>
      </div>
      {verifyDisabledReason ? <p className="warning-inline">{verifyDisabledReason}</p> : null}

      <div className="metric-grid compact-metric-grid">
        <article className="metric-card">
          <h3>Packs</h3>
          <p className="metric">{evidencePacks.length}</p>
          <small>{selectedPack?.runId ?? 'no run linked'}</small>
        </article>
        <article className="metric-card">
          <h3>Signature</h3>
          <p className="metric">{selectedPack?.signatureStatus ?? 'missing'}</p>
          <small>enterprise evidence</small>
        </article>
        <article className="metric-card">
          <h3>Replay</h3>
          <p className="metric">{selectedPack?.replayStatus ?? 'not_available'}</p>
          <small>integrity proof</small>
        </article>
      </div>

      <div className="section-grid two-up">
        <article className="inner-card">
          <h3>Selected pack</h3>
          <div className="metric-list">
            <MetricRow label="Export path" value={selectedPack?.exportPath ?? 'missing'} />
            <MetricRow label="Artifacts" value={String(selectedPack?.artifactCount ?? 0)} />
            <MetricRow label="Hash chain" value={selectedPack?.hashChainStatus ?? 'pending'} />
            <MetricRow label="Claim guard" value={selectedPack?.claimGuardStatus ?? 'blocked'} />
            <MetricRow label="Redaction" value={selectedPack?.redactionStatus ?? 'unknown'} />
          </div>
        </article>
        <article className="inner-card">
          <h3>Verification result</h3>
          <div className="metric-list">
            <MetricRow label="Status" value={verificationStatus} />
            <MetricRow label="Hash chain" value={readBoolLabel(verification, 'hash_chain_verified')} />
            <MetricRow label="Signature" value={readBoolLabel(verification, 'signature_verified')} />
            <MetricRow label="Replay" value={readBoolLabel(verification, 'replay_verified')} />
          </div>
          {verificationBlockingReasons.length > 0 ? (
            <p className="warning-inline">{formatReasonCodeList(verificationBlockingReasons, locale)}</p>
          ) : null}
        </article>
      </div>

      <div className="run-list">
        {blockingReasons.map((reason) => (
          <article className="run-list-item" key={reason}>
            <strong>{reason}</strong>
            <span>{formatReasonCode(reason, locale)}</span>
            <small>{selectedPack ? 'pack blocker' : 'required before ready claim'}</small>
          </article>
        ))}
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

function readBoolLabel(source: Record<string, unknown>, key: string): string {
  if (!(key in source)) {
    return 'not run';
  }
  return source[key] === true ? 'passed' : 'failed';
}
