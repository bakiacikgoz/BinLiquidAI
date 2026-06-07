import { useEffect, useRef } from 'react';

import type { AssistantTurn } from '../../assistant/assistantTypes';
import type { UiLocale } from '../../i18n';
import { AssistantMessage } from './AssistantMessage';

export function AssistantTranscript({
  turns,
  approvalDisabled,
  approvalDisabledReason,
  emptyRunLabel,
  debugRawEnabled,
  locale = 'en',
  onReviewApproval,
  onApprove,
  onReject,
  onExecute,
  onRegenerate,
}: {
  turns: AssistantTurn[];
  approvalDisabled: boolean;
  approvalDisabledReason: string;
  emptyRunLabel: string;
  debugRawEnabled: boolean;
  locale?: UiLocale;
  onReviewApproval: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onExecute: (approvalId: string) => void;
  onRegenerate: (turnId: string) => void;
}) {
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const lastTurnId = turns.at(-1)?.id ?? '';

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript) return;
    const lastTurn = transcript.querySelector<HTMLElement>('[data-assistant-turn="true"]:last-child');
    if (!lastTurn) return;

    const top = Math.max(0, lastTurn.offsetTop - transcript.offsetTop);
    transcript.scrollTo({ top, behavior: 'smooth' });
  }, [lastTurnId]);

  return (
    <div className="assistant-transcript" role="log" aria-live="polite" ref={transcriptRef}>
      {turns.map((turn) => (
        <div key={turn.id} data-assistant-turn="true">
        <AssistantMessage
          turn={turn}
          approvalDisabled={approvalDisabled}
          approvalDisabledReason={approvalDisabledReason}
          emptyRunLabel={emptyRunLabel}
          debugRawEnabled={debugRawEnabled}
          locale={locale}
          onReviewApproval={onReviewApproval}
          onApprove={onApprove}
          onReject={onReject}
          onExecute={onExecute}
          onRegenerate={onRegenerate}
        />
        </div>
      ))}
    </div>
  );
}
