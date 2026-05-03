import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { RuntimeSummaryCard } from './RuntimeSummaryCard';

describe('RuntimeSummaryCard', () => {
  it('does not render raw JSON by default', () => {
    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        items={[{ id: 'summary', tone: 'success', text: 'Çalışma bağlamı doğrulandı.' }]}
        rawJson={{ secret_payload: 'SECRET_VALUE' }}
      />,
    );

    expect(html).toContain('Ham JSON');
    expect(html).not.toContain('secret_payload');
    expect(html).not.toContain('SECRET_VALUE');
  });

  it('can render raw JSON when disclosure state is open', () => {
    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        defaultShowRaw
        items={[{ id: 'summary', tone: 'success', text: 'Çalışma bağlamı doğrulandı.' }]}
        rawJson={{ raw_visible: true }}
      />,
    );

    expect(html).toContain('raw_visible');
  });
});
