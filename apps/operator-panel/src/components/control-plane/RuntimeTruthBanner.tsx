import { describeDataSource } from '../../control-plane/dataSource';
import { formatReasonCodeList } from '../../control-plane/reasonCodes';
import type { ControlPlaneSnapshot, PageViewModel } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';

type RuntimeTruthBannerProps = {
  viewModel: PageViewModel<ControlPlaneSnapshot> | null;
  locale: UiLocale;
};

export function RuntimeTruthBanner({ viewModel, locale }: RuntimeTruthBannerProps) {
  if (!viewModel) {
    return (
      <aside className="runtime-truth-banner runtime-truth-banner-loading" data-testid="runtime-truth-banner">
        <strong>Runtime source</strong>
        <span>Loading control-plane snapshot source...</span>
      </aside>
    );
  }

  const source = viewModel.dataSource;
  const tone = source.isSilentFallback || source.mode === 'error' ? 'danger' : source.isMock || source.freshness === 'stale' ? 'warning' : 'ok';
  const partialReasons = viewModel.data.partialReasons;

  return (
    <aside className={`runtime-truth-banner runtime-truth-banner-${tone}`} data-testid="runtime-truth-banner">
      <div>
        <strong>Runtime source</strong>
        <span>{describeDataSource(source)}</span>
        {viewModel.error ? <span>{`${viewModel.error.code}: ${viewModel.error.message}`}</span> : null}
      </div>
      <dl>
        <div>
          <dt>Mode</dt>
          <dd>{source.mode}</dd>
        </div>
        <div>
          <dt>Freshness</dt>
          <dd>{source.freshness}</dd>
        </div>
        <div>
          <dt>Contract</dt>
          <dd>{source.contractVersion}</dd>
        </div>
        <div>
          <dt>Last refresh</dt>
          <dd>{source.lastRefreshUtc ?? 'unknown'}</dd>
        </div>
        {partialReasons.length > 0 ? (
          <div>
            <dt>Partial reasons</dt>
            <dd>{formatReasonCodeList(partialReasons.slice(0, 3), locale)}</dd>
          </div>
        ) : null}
      </dl>
    </aside>
  );
}
