import type { AssistantTurnStatus } from '../../assistant/assistantTypes';

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
  startedAtUtc,
  completedAtUtc,
}: {
  status: AssistantTurnStatus;
  startedAtUtc: string;
  completedAtUtc: string | null;
}) {
  const isThinking = status === 'starting' || status === 'streaming';
  return (
    <div className={isThinking ? 'assistant-running-state assistant-running-state-active' : 'assistant-running-state'}>
      <span className="assistant-thinking-label">{thinkingLabel(status, startedAtUtc, completedAtUtc)}</span>
    </div>
  );
}
