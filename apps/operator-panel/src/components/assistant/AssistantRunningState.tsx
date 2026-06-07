import type { AssistantTimelineItem, AssistantTurnStatus } from '../../assistant/assistantTypes';
import { translateAssistantText, type UiLocale } from '../../i18n';
import { StatusDot } from '../primitives/StatusDot';

function normalizeStatusLabel(value: string): string {
  return value.replace(/_/g, ' ').trim().toLowerCase();
}

function isBoilerplateTimelineItem(item: AssistantTimelineItem): boolean {
  const title = normalizeStatusLabel(item.title);
  const subtitle = normalizeStatusLabel(item.subtitle);
  return title === 'starting' && subtitle === 'starting assistant turn';
}

function secondsBetween(startedAtUtc: string, completedAtUtc: string | null): number | null {
  const startedAt = new Date(startedAtUtc).getTime();
  const completedAt = completedAtUtc ? new Date(completedAtUtc).getTime() : Date.now();

  if (Number.isNaN(startedAt) || Number.isNaN(completedAt)) {
    return null;
  }

  return Math.max(1, Math.round((completedAt - startedAt) / 1000));
}

function thinkingLabel(status: AssistantTurnStatus, startedAtUtc: string, completedAtUtc: string | null): string {
  if (status === 'starting' || status === 'streaming') {
    return 'Düşünüyor';
  }

  if (status === 'completed') {
    const seconds = secondsBetween(startedAtUtc, completedAtUtc);
    return seconds ? `${seconds} saniye düşündü` : 'Düşündü';
  }

  if (status === 'awaiting_approval') return 'Onay bekliyor';
  if (status === 'failed') return 'Yanıt tamamlanamadı';
  if (status === 'cancelled') return 'Yanıt iptal edildi';
  return 'Hazır';
}

export function AssistantRunningState({
  status,
  timeline,
  startedAtUtc,
  completedAtUtc,
  locale = 'en',
}: {
  status: AssistantTurnStatus;
  timeline: AssistantTimelineItem[];
  startedAtUtc: string;
  completedAtUtc: string | null;
  locale?: UiLocale;
}) {
  const statusLabel = normalizeStatusLabel(status);
  const visibleTimeline = timeline
    .filter((item) => normalizeStatusLabel(item.title) !== statusLabel && !isBoilerplateTimelineItem(item))
    .slice(-5);
  const isThinking = status === 'starting' || status === 'streaming';
  return (
    <div className={isThinking ? 'assistant-running-state assistant-running-state-active' : 'assistant-running-state'}>
      <span className="assistant-thinking-label">{thinkingLabel(status, startedAtUtc, completedAtUtc)}</span>
      {visibleTimeline.length > 0 ? (
        <div className="assistant-activity-list">
          {visibleTimeline.map((item) => (
            <div className="assistant-activity-row" key={item.id}>
              <StatusDot tone={item.tone} />
              <span>
                <strong>{translateAssistantText(item.title, locale)}</strong>
                <em>{translateAssistantText(item.subtitle, locale)}</em>
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
