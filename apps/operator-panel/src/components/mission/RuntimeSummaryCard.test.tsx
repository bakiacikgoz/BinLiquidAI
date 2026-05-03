import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { redactJson } from '../../redactJson';
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
    expect(html).toContain('disabled=""');
    expect(html).not.toContain('secret_payload');
    expect(html).not.toContain('SECRET_VALUE');
  });

  it('can render redacted raw JSON only when debug disclosure state is open', () => {
    const html = renderToStaticMarkup(
      <RuntimeSummaryCard
        debugRawEnabled
        defaultShowRaw
        items={[{ id: 'summary', tone: 'success', text: 'Çalışma bağlamı doğrulandı.' }]}
        rawJson={{ raw_visible: true, api_token: 'SECRET_VALUE' }}
      />,
    );

    expect(html).toContain('raw_visible');
    expect(html).toContain('[redacted]');
    expect(html).not.toContain('SECRET_VALUE');
  });

  it('redacts nested sensitive keys before rendering', () => {
    expect(redactJson({ nested: { password: 'SECRET_VALUE' }, safe: 'ok' })).toEqual({
      nested: { password: '[redacted]' },
      safe: 'ok',
    });
  });
});
