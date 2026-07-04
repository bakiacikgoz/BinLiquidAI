import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';

import type { AssistantTurn } from '../../assistant/assistantTypes';
import type { UiLocale } from '../../i18n';
import { AssistantMessage } from './AssistantMessage';

const LATEST_THRESHOLD_PX = 96;

function bottomGap(element: HTMLElement): number {
  return element.scrollHeight - element.clientHeight - element.scrollTop;
}

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
  const isAtLatestRef = useRef(true);
  const previousLastTurnIdRef = useRef('');
  const userNavigatedTranscriptRef = useRef(false);
  const [isAtLatest, setIsAtLatest] = useState(true);
  const lastTurnId = turns.at(-1)?.id ?? '';
  const transcriptContentKey = useMemo(
    () =>
      turns
        .map((turn) =>
          [
            turn.id,
            turn.status,
            turn.userMessage.text.length,
            turn.assistantMessage.text.length,
            turn.assistantMessage.referencedRuns.length,
            turn.assistantMessage.referencedArtifacts.length,
            turn.assistantMessage.warning ?? '',
            turn.assistantMessage.error?.code ?? '',
            turn.assistantMessage.approval?.approvalId ?? '',
            turn.assistantMessage.proposedAction?.id ?? '',
          ].join(':'),
        )
        .join('|'),
    [turns],
  );

  const updateLatestState = useCallback(() => {
    const transcript = transcriptRef.current;
    if (!transcript) {
      return;
    }
    const next = bottomGap(transcript) <= LATEST_THRESHOLD_PX;
    if (!next && !userNavigatedTranscriptRef.current) {
      isAtLatestRef.current = true;
      setIsAtLatest(true);
      return;
    }
    if (next) {
      userNavigatedTranscriptRef.current = false;
    }
    isAtLatestRef.current = next;
    setIsAtLatest(next);
  }, []);

  const scrollToLatest = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const transcript = transcriptRef.current;
    if (!transcript) {
      return;
    }
    transcript.scrollTo({ top: transcript.scrollHeight, behavior });
    userNavigatedTranscriptRef.current = false;
    isAtLatestRef.current = true;
    setIsAtLatest(true);
  }, []);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript) {
      return undefined;
    }
    const markUserNavigation = () => {
      userNavigatedTranscriptRef.current = true;
    };
    transcript.addEventListener('scroll', updateLatestState, { passive: true });
    transcript.addEventListener('wheel', markUserNavigation, { passive: true });
    transcript.addEventListener('touchstart', markUserNavigation, { passive: true });
    transcript.addEventListener('pointerdown', markUserNavigation, { passive: true });
    transcript.addEventListener('keydown', markUserNavigation);
    updateLatestState();
    return () => {
      transcript.removeEventListener('scroll', updateLatestState);
      transcript.removeEventListener('wheel', markUserNavigation);
      transcript.removeEventListener('touchstart', markUserNavigation);
      transcript.removeEventListener('pointerdown', markUserNavigation);
      transcript.removeEventListener('keydown', markUserNavigation);
    };
  }, [updateLatestState]);

  useLayoutEffect(() => {
    const lastTurnChanged = previousLastTurnIdRef.current !== lastTurnId;
    previousLastTurnIdRef.current = lastTurnId;
    if (!lastTurnId) {
      return;
    }
    if (lastTurnChanged) {
      if (userNavigatedTranscriptRef.current && !isAtLatestRef.current) {
        updateLatestState();
        return;
      }
      scrollToLatest('auto');
      return;
    }
    if (isAtLatestRef.current) {
      scrollToLatest('auto');
      return;
    }
    updateLatestState();
  }, [lastTurnId, scrollToLatest, transcriptContentKey, updateLatestState]);

  useEffect(() => {
    const transcript = transcriptRef.current;
    if (!transcript || typeof ResizeObserver === 'undefined') {
      return undefined;
    }
    const observer = new ResizeObserver(() => {
      if (isAtLatestRef.current) {
        scrollToLatest('auto');
      } else {
        updateLatestState();
      }
    });
    observer.observe(transcript);
    const lastTurn = transcript.querySelector<HTMLElement>('[data-assistant-turn="true"]:last-child');
    if (lastTurn) {
      observer.observe(lastTurn);
    }
    return () => observer.disconnect();
  }, [lastTurnId, scrollToLatest, updateLatestState]);

  return (
    <div className="assistant-transcript-shell">
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
      {!isAtLatest ? (
        <button type="button" className="assistant-jump-latest" onClick={() => scrollToLatest()}>
          {locale === 'tr' ? 'En yeniye git' : 'Jump to latest'}
        </button>
      ) : null}
    </div>
  );
}
