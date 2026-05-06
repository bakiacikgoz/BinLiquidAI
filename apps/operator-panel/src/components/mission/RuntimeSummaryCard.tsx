import { useEffect, useState } from 'react';

import { Badge, type BadgeTone } from '../primitives/Badge';
import { Icon } from '../primitives/Icon';
import { SectionHeader } from '../primitives/SectionHeader';
import { redactJson } from '../../redactJson';

export type RuntimeSummaryItem = {
  id: string;
  tone: 'success' | 'warning' | 'info';
  text: string;
  badge?: string;
  badgeTone?: BadgeTone;
};

export function RuntimeSummaryCard({
  items,
  rawJson,
  debugRawEnabled = false,
  defaultShowRaw = false,
  onRawJsonRequested,
}: {
  items: RuntimeSummaryItem[];
  rawJson: unknown;
  debugRawEnabled?: boolean;
  defaultShowRaw?: boolean;
  onRawJsonRequested?: () => boolean;
}) {
  const [showRaw, setShowRaw] = useState(debugRawEnabled && defaultShowRaw);

  useEffect(() => {
    if (!debugRawEnabled && showRaw) {
      setShowRaw(false);
    }
  }, [debugRawEnabled, showRaw]);

  function toggleRaw() {
    if (showRaw) {
      setShowRaw(false);
      return;
    }

    if (!debugRawEnabled) {
      return;
    }

    if (onRawJsonRequested && !onRawJsonRequested()) {
      return;
    }

    setShowRaw(true);
  }

  return (
    <div className="mc-card runtime-summary-card">
      <SectionHeader
        title="RUNTIME ÖZETİ"
        action={
          <button
            className="raw-toggle"
            type="button"
            disabled={!debugRawEnabled}
            title={debugRawEnabled ? undefined : 'Ham payload modu ayarlardan açılmalı.'}
            onClick={toggleRaw}
          >
            {showRaw ? "Ham JSON'u Gizle" : "Ham JSON'u Görüntüle"} <Icon name="chevron" />
          </button>
        }
      />
      <ul className="runtime-summary-list">
        {items.map((item) => (
          <li className={`runtime-summary-item runtime-summary-item-${item.tone}`} key={item.id}>
            <Icon name={item.tone === 'warning' ? 'alert' : 'check'} />
            <span className="runtime-summary-copy">
              <span className="runtime-summary-text">{item.text}</span>
              {item.badge ? <Badge tone={item.badgeTone ?? item.tone}>{item.badge}</Badge> : null}
            </span>
          </li>
        ))}
      </ul>
      {showRaw ? (
        <pre className="json-panel runtime-raw-panel">{JSON.stringify(redactJson(rawJson ?? {}), null, 2)}</pre>
      ) : null}
    </div>
  );
}
