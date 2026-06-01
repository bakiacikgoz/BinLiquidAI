import type { DataSourceState } from './types';

export class SilentMockFallbackError extends Error {
  readonly source: DataSourceState;

  constructor(source: DataSourceState) {
    super('Live control-plane data fell back to preview/mock data.');
    this.name = 'SilentMockFallbackError';
    this.source = source;
  }
}

export function assertNoSilentMockFallback(source: DataSourceState): void {
  if (source.isSilentFallback) {
    throw new SilentMockFallbackError(source);
  }
}

export function isLiveSource(source: DataSourceState): boolean {
  return source.mode === 'tauri_live' || source.mode === 'cli_live';
}

export function describeDataSource(source: DataSourceState): string {
  if (source.isSilentFallback) {
    return 'Live mode used preview data and must fail closed.';
  }
  if (source.mode === 'preview_fixture') {
    return 'Preview fixture data. Do not use as live evidence.';
  }
  if (source.mode === 'stale_cache') {
    return 'Stale cached control-plane data.';
  }
  if (source.mode === 'error') {
    return source.sourceReason || 'Control-plane source is unavailable.';
  }
  return source.sourceReason || 'Live control-plane snapshot.';
}
