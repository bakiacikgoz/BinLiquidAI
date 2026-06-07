import { describeDataSource } from '../../control-plane/dataSource';
import { formatReasonCodeList } from '../../control-plane/reasonCodes';
import type { ControlPlaneSnapshot, PageViewModel } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';
import { CodeToken, ReasonChip, StatusBadge } from '../primitives/Token';

type RuntimeTruthBannerProps = {
  viewModel: PageViewModel<ControlPlaneSnapshot> | null;
  locale: UiLocale;
};

export function RuntimeTruthBanner({ viewModel, locale }: RuntimeTruthBannerProps) {
  if (!viewModel) {
    return (
      <aside className="runtime-truth-banner runtime-truth-banner-loading" data-testid="runtime-truth-banner">
        <div className="runtime-truth-summary">
          <div className="runtime-truth-copy">
            <strong>Runtime source</strong>
            <span>Loading control-plane snapshot source...</span>
          </div>
        </div>
      </aside>
    );
  }

  const source = viewModel.dataSource;
  const tone = source.isSilentFallback || source.mode === 'error' ? 'danger' : source.isMock || source.freshness === 'stale' ? 'warning' : 'ok';
  const partialReasons = viewModel.data.partialReasons;
  const reasonSummary = partialReasons.length > 0 ? formatReasonCodeList(partialReasons.slice(0, 3), locale) : '';
  const statusTone = tone === 'danger' ? 'error' : tone === 'warning' ? 'warning' : 'success';

  return (
    <aside className={`runtime-truth-banner runtime-truth-banner-${tone}`} data-testid="runtime-truth-banner">
      <div className="runtime-truth-summary">
        <div className="runtime-truth-copy">
          <strong>Runtime source</strong>
          <span>{describeDataSource(source)}</span>
          {viewModel.error ? <span>{`${viewModel.error.code}: ${viewModel.error.message}`}</span> : null}
        </div>
        <dl className="runtime-truth-meta" aria-label="Runtime source summary">
          <div>
            <dt>Mode</dt>
            <dd>
              <CodeToken>{source.mode}</CodeToken>
            </dd>
          </div>
          <div>
            <dt>Freshness</dt>
            <dd>
              <StatusBadge tone={statusTone}>{source.freshness}</StatusBadge>
            </dd>
          </div>
          {partialReasons.length > 0 ? (
            <div className="runtime-truth-reasons">
              <dt>Partial reasons</dt>
              <dd>
                <ReasonChip title={formatReasonCodeList([partialReasons[0]], locale)}>{partialReasons[0]}</ReasonChip>
                {partialReasons.length > 1 ? <StatusBadge tone="muted">{`+${partialReasons.length - 1}`}</StatusBadge> : null}
              </dd>
            </div>
          ) : null}
        </dl>
      </div>
      <details className="runtime-truth-details">
        <summary>Details</summary>
        <dl>
          <div>
            <dt>Contract</dt>
            <dd>
              <CodeToken>{source.contractVersion}</CodeToken>
            </dd>
          </div>
          <div>
            <dt>Last refresh</dt>
            <dd>{source.lastRefreshUtc ?? 'unknown'}</dd>
          </div>
          <div>
            <dt>Silent fallback</dt>
            <dd>{source.isSilentFallback ? 'yes' : 'no'}</dd>
          </div>
          <div>
            <dt>Mock</dt>
            <dd>{source.isMock ? 'yes' : 'no'}</dd>
          </div>
          {partialReasons.length > 0 ? (
            <div>
              <dt>Partial reasons</dt>
              <dd>{reasonSummary}</dd>
            </div>
          ) : null}
        </dl>
      </details>
    </aside>
  );
}
