import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { StageProgress } from './StageProgress';

describe('StageProgress', () => {
  it('renders mission control stage labels', () => {
    const html = renderToStaticMarkup(<StageProgress currentStage="approval" />);

    expect(html).toContain('Planlama');
    expect(html).toContain('Hazırlık');
    expect(html).toContain('Çalıştırma');
    expect(html).toContain('Onay');
    expect(html).toContain('Tamamlandı');
    expect(html).toContain('mission-stage-node-active');
  });
});
