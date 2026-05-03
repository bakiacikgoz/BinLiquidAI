import { useState } from 'react';

import { Icon } from '../primitives/Icon';
import { SectionHeader } from '../primitives/SectionHeader';

export type RuntimeSummaryItem = {
  id: string;
  tone: 'success' | 'warning' | 'info';
  text: string;
};

export function RuntimeSummaryCard({
  items,
  rawJson,
  defaultShowRaw = false,
}: {
  items: RuntimeSummaryItem[];
  rawJson: unknown;
  defaultShowRaw?: boolean;
}) {
  const [showRaw, setShowRaw] = useState(defaultShowRaw);

  return (
    <div className="mc-card runtime-summary-card">
      <SectionHeader
        title="RUNTIME ÖZETİ"
        action={
          <button className="raw-toggle" type="button" onClick={() => setShowRaw((value) => !value)}>
            Ham JSON'u Görüntüle <Icon name="chevron" />
          </button>
        }
      />
      <ul className="runtime-summary-list">
        {items.map((item) => (
          <li className={`runtime-summary-item runtime-summary-item-${item.tone}`} key={item.id}>
            <Icon name={item.tone === 'warning' ? 'alert' : 'check'} />
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
      {showRaw ? <pre className="json-panel runtime-raw-panel">{JSON.stringify(rawJson ?? {}, null, 2)}</pre> : null}
    </div>
  );
}
