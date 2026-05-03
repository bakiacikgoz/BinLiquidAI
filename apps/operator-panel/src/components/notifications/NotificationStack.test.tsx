import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { NotificationStack } from './NotificationStack';

describe('NotificationStack', () => {
  it('renders dismissable operational notifications', () => {
    const html = renderToStaticMarkup(
      <NotificationStack
        items={[
          {
            id: 'approval',
            kind: 'warning',
            title: 'Onay talebi oluşturuldu',
            subtitle: 'Kullanıcı onayı bekleniyor.',
            time: 'şimdi',
          },
        ]}
        onDismiss={() => undefined}
      />,
    );

    expect(html).toContain('Onay talebi oluşturuldu');
    expect(html).toContain('Bildirimi kapat');
  });
});
