import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { MissionControlView, type MissionControlViewProps } from './MissionControlView';

const baseProps: MissionControlViewProps = {
  runOptions: [{ id: 'run_2025_05_14_001', label: 'run_2025_05_14_001' }],
  selectedRunId: 'run_2025_05_14_001',
  sessionId: 'session_7f3a',
  sessionStatus: 'Çalışıyor',
  objective: 'Yönetişimli görevi tarif edin.',
  priority: 'Yüksek',
  targetType: 'Yönetişimli Görev',
  statusCode: 'CLIJ.NOT_FOUND',
  statusError: 'Hata: No such file or directory (os error 2)',
  stageLabel: 'İnceleme',
  stageKey: 'planning',
  startedAt: '14 May 2025 14:32',
  duration: '00:03:18',
  progress: 24,
  activityItems: [
    {
      id: 'activity',
      time: '14:35:12',
      title: 'Planlama adımı başlatıldı.',
      body: 'Ajan görevi analiz ediyor.',
      tone: 'info',
    },
  ],
  sessionEvents: [
    {
      id: 'event',
      time: '14:35',
      title: 'Planlama aşaması geçildi',
      body: 'Görev analizi tamamlandı.',
      tag: 'SİSTEM',
      tone: 'info',
    },
  ],
  sessionEventFilter: 'all',
  sessionEventsHasMore: false,
  sessionEventsLoadingMore: false,
  runtimeSummary: [{ id: 'summary', tone: 'success', text: 'Çalışma bağlamı doğrulandı.' }],
  rawSummary: { hidden: true },
  debugRawEnabled: true,
  hasApproval: true,
  approvalLabel: 'Plan gözden geçir ve çalıştırmaya izin ver.',
  approvalDisabled: false,
  approvalDisabledReason: '',
  onSelectRun: () => undefined,
  onRawJsonRequested: () => true,
  onSessionEventFilterChange: () => undefined,
  onLoadMoreSessionEvents: () => undefined,
  onApprove: () => undefined,
  onEditApproval: () => undefined,
  onReject: () => undefined,
};

describe('MissionControlView', () => {
  it('renders the pending approval CTA when approval exists', () => {
    const html = renderToStaticMarkup(<MissionControlView {...baseProps} />);

    expect(html).toContain('ONAY KAPISI');
    expect(html).toContain('Onayla ve Devam Et');
    expect(html).toMatch(/<button class="mc-button mc-button-primary" type="button">[\s\S]*Onayla ve Devam Et/);
  });

  it('disables approval CTA when mutations are blocked', () => {
    const html = renderToStaticMarkup(
      <MissionControlView {...baseProps} approvalDisabled approvalDisabledReason="Operatör ID gerekli." />,
    );

    expect(html).toContain('Operatör ID gerekli.');
    expect(html).toContain('disabled=""');
  });
});
