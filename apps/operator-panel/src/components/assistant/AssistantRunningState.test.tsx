import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { AssistantRunningState } from './AssistantRunningState';

describe('AssistantRunningState', () => {
  it('does not repeat the current status as a timeline row', () => {
    const html = renderToStaticMarkup(
      <AssistantRunningState
        status="starting"
        startedAtUtc="2026-03-08T09:31:00.000Z"
        completedAtUtc={null}
        timeline={[
          {
            id: 'turn-starting',
            tone: 'info',
            title: 'Starting',
            subtitle: 'Starting assistant turn',
            timestampUtc: '2026-03-08T09:31:00.000Z',
          },
        ]}
      />,
    );

    expect(html).toContain('Düşünüyor');
    expect(html).not.toContain('starting');
    expect(html).not.toContain('assistant-activity-row');
    expect(html).not.toContain('Starting assistant turn');
  });

  it('keeps timeline rows that add information beyond the current status', () => {
    const html = renderToStaticMarkup(
      <AssistantRunningState
        status="streaming"
        startedAtUtc="2026-03-08T09:31:00.000Z"
        completedAtUtc={null}
        timeline={[
          {
            id: 'turn-router',
            tone: 'info',
            title: 'Routing request',
            subtitle: 'Selecting assistant execution path',
            timestampUtc: '2026-03-08T09:31:00.000Z',
          },
        ]}
      />,
    );

    expect(html).toContain('Düşünüyor');
    expect(html).not.toContain('streaming');
    expect(html).toContain('Routing request');
    expect(html).toContain('Selecting assistant execution path');
  });

  it('renders completed thinking duration without the active shimmer state', () => {
    const html = renderToStaticMarkup(
      <AssistantRunningState
        status="completed"
        startedAtUtc="2026-03-08T09:31:00.000Z"
        completedAtUtc="2026-03-08T09:31:04.000Z"
        timeline={[
          {
            id: 'turn-starting',
            tone: 'info',
            title: 'Starting',
            subtitle: 'Starting assistant turn',
            timestampUtc: '2026-03-08T09:31:00.000Z',
          },
        ]}
      />,
    );

    expect(html).toContain('4 saniye düşündü');
    expect(html).not.toContain('Starting assistant turn');
    expect(html).not.toContain('assistant-running-state-active');
  });
});
