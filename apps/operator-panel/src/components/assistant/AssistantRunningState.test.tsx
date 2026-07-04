import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { AssistantRunningState } from './AssistantRunningState';

describe('AssistantRunningState', () => {
  it('renders the current thinking state without activity rows', () => {
    const html = renderToStaticMarkup(
      <AssistantRunningState
        status="starting"
        startedAtUtc="2026-03-08T09:31:00.000Z"
        completedAtUtc={null}
      />,
    );

    expect(html).toContain('Düşünüyor');
    expect(html).not.toContain('starting');
    expect(html).not.toContain('assistant-activity-row');
  });

  it('renders completed thinking duration without the active shimmer state', () => {
    const html = renderToStaticMarkup(
      <AssistantRunningState
        status="completed"
        startedAtUtc="2026-03-08T09:31:00.000Z"
        completedAtUtc="2026-03-08T09:31:04.000Z"
      />,
    );

    expect(html).toContain('4 saniye düşündü');
    expect(html).not.toContain('assistant-running-state-active');
  });
});
