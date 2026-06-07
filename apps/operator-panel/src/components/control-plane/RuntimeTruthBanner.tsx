import { describeDataSource } from '../../control-plane/dataSource';
import { formatReasonCodeList } from '../../control-plane/reasonCodes';
import type { ControlPlaneSnapshot, PageViewModel } from '../../control-plane/types';
import type { UiLocale } from '../../i18n';
import { CodeToken, ReasonChip, StatusBadge } from '../primitives/Token';

type RuntimeTruthBannerProps = {
  viewModel: PageViewModel<ControlPlaneSnapshot> | null;
  locale: UiLocale;
};

const copy = {
  en: {
    runtimeSource: 'Runtime source',
    loading: 'Loading control-plane snapshot source...',
    runtimeSourceSummary: 'Runtime source summary',
    mode: 'Mode',
    freshness: 'Freshness',
    partialReasons: 'Partial reasons',
    details: 'Details',
    contract: 'Contract',
    lastRefresh: 'Last refresh',
    unknown: 'unknown',
    silentFallback: 'Silent fallback',
    yes: 'yes',
    no: 'no',
    mock: 'Mock',
    liveFallback: 'Live mode used preview data and must fail closed.',
    liveFallbackCompact: 'Preview fallback',
    previewFixture: 'Preview fixture data. Do not use as live evidence.',
    previewFixtureCompact: 'Preview data',
    staleCache: 'Stale cached control-plane data.',
    staleCacheCompact: 'Stale cache',
    unavailable: 'Control-plane source is unavailable.',
    unavailableCompact: 'Source unavailable',
    liveSnapshot: 'Live control-plane snapshot.',
    liveSnapshotCompact: 'Live snapshot',
  },
  tr: {
    runtimeSource: 'Runtime kaynağı',
    loading: 'Control-plane snapshot kaynağı yükleniyor...',
    runtimeSourceSummary: 'Runtime kaynağı özeti',
    mode: 'Mod',
    freshness: 'Güncellik',
    partialReasons: 'Kısmi nedenler',
    details: 'Detaylar',
    contract: 'Sözleşme',
    lastRefresh: 'Son yenileme',
    unknown: 'bilinmiyor',
    silentFallback: 'Sessiz fallback',
    yes: 'evet',
    no: 'hayır',
    mock: 'Mock',
    liveFallback: 'Live mod önizleme verisi kullandı ve kapalı şekilde başarısız olmalı.',
    liveFallbackCompact: 'Önizleme fallback',
    previewFixture: 'Önizleme fixture verisi. Live kanıt olarak kullanmayın.',
    previewFixtureCompact: 'Önizleme verisi',
    staleCache: 'Eski control-plane cache verisi.',
    staleCacheCompact: 'Eski cache',
    unavailable: 'Control-plane kaynağı kullanılamıyor.',
    unavailableCompact: 'Kaynak yok',
    liveSnapshot: 'Live control-plane snapshot.',
    liveSnapshotCompact: 'Live snapshot',
  },
} satisfies Record<UiLocale, Record<string, string>>;

function describeDataSourceForLocale(
  source: ControlPlaneSnapshot['dataSource'],
  locale: UiLocale,
  variant: 'compact' | 'full' = 'full',
): string {
  const text = copy[locale];
  if (locale === 'en') {
    if (variant === 'compact') {
      if (source.isSilentFallback) return text.liveFallbackCompact;
      if (source.mode === 'preview_fixture') return text.previewFixtureCompact;
      if (source.mode === 'stale_cache') return text.staleCacheCompact;
      if (source.mode === 'error') return text.unavailableCompact;
      return text.liveSnapshotCompact;
    }
    return describeDataSource(source);
  }
  if (source.isSilentFallback) {
    return variant === 'compact' ? text.liveFallbackCompact : text.liveFallback;
  }
  if (source.mode === 'preview_fixture') {
    return variant === 'compact' ? text.previewFixtureCompact : text.previewFixture;
  }
  if (source.mode === 'stale_cache') {
    return variant === 'compact' ? text.staleCacheCompact : text.staleCache;
  }
  if (source.mode === 'error') {
    return variant === 'compact' ? text.unavailableCompact : source.sourceReason || text.unavailable;
  }
  return variant === 'compact' ? text.liveSnapshotCompact : source.sourceReason || text.liveSnapshot;
}

export function RuntimeTruthBanner({ viewModel, locale }: RuntimeTruthBannerProps) {
  const text = copy[locale];
  if (!viewModel) {
    return (
      <aside className="runtime-truth-banner runtime-truth-banner-loading" data-testid="runtime-truth-banner">
        <div className="runtime-truth-summary">
          <div className="runtime-truth-copy">
            <strong>{text.runtimeSource}</strong>
            <span>{text.loading}</span>
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
          <strong>{text.runtimeSource}</strong>
          <span title={describeDataSourceForLocale(source, locale)}>
            {describeDataSourceForLocale(source, locale, 'compact')}
          </span>
          {viewModel.error ? <span>{`${viewModel.error.code}: ${viewModel.error.message}`}</span> : null}
        </div>
        <dl className="runtime-truth-meta" aria-label={text.runtimeSourceSummary}>
          <div>
            <dt>{text.mode}</dt>
            <dd>
              <CodeToken>{source.mode}</CodeToken>
            </dd>
          </div>
          <div>
            <dt>{text.freshness}</dt>
            <dd>
              <StatusBadge tone={statusTone}>{source.freshness}</StatusBadge>
            </dd>
          </div>
          {partialReasons.length > 0 ? (
            <div className="runtime-truth-reasons">
              <dt>{text.partialReasons}</dt>
              <dd>
                <ReasonChip title={formatReasonCodeList([partialReasons[0]], locale)}>{partialReasons[0]}</ReasonChip>
                {partialReasons.length > 1 ? <StatusBadge tone="muted">{`+${partialReasons.length - 1}`}</StatusBadge> : null}
              </dd>
            </div>
          ) : null}
        </dl>
      </div>
      <details className="runtime-truth-details">
        <summary>{text.details}</summary>
        <dl>
          <div>
            <dt>{text.contract}</dt>
            <dd>
              <CodeToken>{source.contractVersion}</CodeToken>
            </dd>
          </div>
          <div>
            <dt>{text.lastRefresh}</dt>
            <dd>{source.lastRefreshUtc ?? text.unknown}</dd>
          </div>
          <div>
            <dt>{text.silentFallback}</dt>
            <dd>{source.isSilentFallback ? text.yes : text.no}</dd>
          </div>
          <div>
            <dt>{text.mock}</dt>
            <dd>{source.isMock ? text.yes : text.no}</dd>
          </div>
          {partialReasons.length > 0 ? (
            <div className="runtime-truth-detail-reasons">
              <dt>{text.partialReasons}</dt>
              <dd>{reasonSummary}</dd>
            </div>
          ) : null}
        </dl>
      </details>
    </aside>
  );
}
