import { useEffect, useState } from 'react';

import { Badge, type BadgeTone } from '../primitives/Badge';
import { Icon } from '../primitives/Icon';
import { SectionHeader } from '../primitives/SectionHeader';
import { redactJson } from '../../redactJson';
import type { ComputerUseCapabilityResolution } from '../../capabilities';

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
  computerUseCapabilityResolution,
  debugRawEnabled = false,
  defaultShowRaw = false,
  onRawJsonRequested,
}: {
  items: RuntimeSummaryItem[];
  rawJson: unknown;
  computerUseCapabilityResolution?: ComputerUseCapabilityResolution | null;
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
      {computerUseCapabilityResolution ? (
        <ComputerUseCapabilityPanel resolution={computerUseCapabilityResolution} />
      ) : null}
      {showRaw ? (
        <pre className="json-panel runtime-raw-panel">{JSON.stringify(redactJson(rawJson ?? {}), null, 2)}</pre>
      ) : null}
    </div>
  );
}

function ComputerUseCapabilityPanel({ resolution }: { resolution: ComputerUseCapabilityResolution }) {
  const blockers = resolution.blockers.slice(0, 3);
  const statusTone: BadgeTone =
    resolution.liveEnabled || resolution.status === 'pass'
      ? 'success'
      : resolution.status === 'fail'
        ? 'error'
        : 'warning';

  return (
    <section className="computer-use-capability-panel" aria-label="Computer-use capability">
      <div className="computer-use-capability-header">
        <span>Computer-use capability</span>
        <Badge tone={statusTone}>{resolution.status}</Badge>
      </div>
      <dl className="computer-use-capability-grid">
        <CapabilityMetric label="Platform" value={resolution.platform} />
        <CapabilityMetric label="Live execution" value={resolution.liveEnabled ? 'Enabled' : 'Disabled'} />
        <CapabilityMetric
          label="Supervised live"
          value={resolution.supervisedLiveAllowed ? 'Allowed' : 'Blocked'}
        />
        <CapabilityMetric label="Public live claim" value={resolution.publicLiveClaimAllowed ? 'Yes' : 'No'} />
        <CapabilityMetric label="Evidence" value={`${resolution.evidence.status} / ${resolution.evidence.source}`} />
        <CapabilityMetric
          label="Config"
          value={`${resolution.config.provider} / ${resolution.config.captureBackend}+${resolution.config.inputBackend}`}
        />
        <CapabilityMetric
          label="Driver"
          value={resolution.driver.ready ? 'Ready' : 'Not ready'}
        />
        <CapabilityMetric
          label="Safety"
          value={
            resolution.safety.failClosed && !resolution.safety.rawScreenshotPersistenceAllowed
              ? 'Fail-closed, raw screenshots disabled'
              : 'Fail-closed required'
          }
        />
      </dl>
      {resolution.reasonCode ? <p className="computer-use-capability-reason">{resolution.reasonCode}</p> : null}
      {blockers.length > 0 ? (
        <div className="computer-use-capability-blockers" aria-label="Computer-use blockers">
          {blockers.map((blocker) => (
            <Badge tone="warning" key={blocker}>
              {blocker}
            </Badge>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function CapabilityMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="computer-use-capability-metric">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
