import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { Sidebar } from './Sidebar';

describe('Sidebar', () => {
  it('renders AI Assistant as an active nav item without changing badges', () => {
    const html = renderToStaticMarkup(
      <Sidebar
        activeView="assistant"
        open={false}
        collapsed={false}
        operatorId="ops-team-01"
        pendingApprovalCount={2}
        warningCount={3}
        onClose={() => undefined}
        onToggleCollapse={() => undefined}
        onNavigate={() => undefined}
      />,
    );

    expect(html).toContain('AI Assistant');
    expect(html).toContain('premium-nav-item-active');
    expect(html).toContain('>2</em>');
    expect(html).toContain('>3</em>');
  });
});
