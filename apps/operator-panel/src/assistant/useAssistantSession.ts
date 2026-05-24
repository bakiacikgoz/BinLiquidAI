import { useCallback, useEffect, useRef, useState } from 'react';

import {
  listenAssistantEvents,
  startAssistantTurn,
} from '../bridge';
import {
  assistantRuntimeOptionsFromSettings,
  type AssistantRuntimeSettings,
  type PanelSettings,
} from '../settings';
import { buildAssistantPrompt } from './assistantPromptBuilder';
import {
  createAssistantSession,
  createAssistantTurn,
  mapCliAssistantEvent,
  normalizeAssistantError,
  startAssistantTurnLocally,
} from './assistantMappers';
import type { AssistantSessionState, AssistantStartTurnOptions, AssistantStreamEvent } from './assistantTypes';

export type AssistantContextSnapshot = {
  selectedRunId: string;
  selectedRunStatus: unknown | null;
  selectedRunEvents: unknown[];
  selectedArtifacts: Record<string, unknown>;
  pendingApproval: unknown | null;
  systemHealth: unknown | null;
};

export type AssistantSessionActions = {
  send: (message: string, runtimeSettings?: AssistantRuntimeSettings) => Promise<void>;
  newChat: () => void;
  applyEvent: (event: AssistantStreamEvent) => void;
  markApprovalDetailLoaded: (approvalId: string, detail: unknown) => void;
  appendSystemMessage: (message: string) => void;
};

export function useAssistantSession(
  settings: PanelSettings,
  getContext: () => AssistantContextSnapshot,
): { state: AssistantSessionState; actions: AssistantSessionActions } {
  const [state, setState] = useState<AssistantSessionState>(() => createAssistantSession());
  const stateRef = useRef(state);
  const eventQueueRef = useRef<AssistantStreamEvent[]>([]);
  const flushTimerRef = useRef<number | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const flushEvents = useCallback(() => {
    const queued = eventQueueRef.current;
    eventQueueRef.current = [];
    flushTimerRef.current = null;
    if (queued.length === 0) {
      return;
    }
    setState((previous) => queued.reduce((next, event) => mapCliAssistantEvent(event, next), previous));
  }, []);

  const applyEvent = useCallback(
    (event: AssistantStreamEvent) => {
      eventQueueRef.current.push(event);
      if (flushTimerRef.current === null) {
        flushTimerRef.current = window.setTimeout(flushEvents, 50);
      }
    },
    [flushEvents],
  );

  useEffect(() => {
    let cancelled = false;
    let cleanup: (() => void) | undefined;
    void listenAssistantEvents((event) => {
      if (!cancelled) {
        applyEvent(event);
      }
    }).then((unlisten) => {
      cleanup = unlisten;
    });
    return () => {
      cancelled = true;
      if (flushTimerRef.current !== null) {
        window.clearTimeout(flushTimerRef.current);
      }
      cleanup?.();
    };
  }, [applyEvent]);

  const send = useCallback(
    async (message: string, runtimeSettings?: AssistantRuntimeSettings) => {
      const userMessage = message.trim();
      if (!userMessage || ['starting', 'streaming'].includes(stateRef.current.status)) {
        return;
      }

      const context = getContext();
      const turn = createAssistantTurn({
        sessionId: stateRef.current.sessionId,
        userMessage,
      });
      const nextState = startAssistantTurnLocally(stateRef.current, turn);
      const nextStateWithContext = {
        ...nextState,
        selectedRunIds: context.selectedRunId
          ? Array.from(new Set([context.selectedRunId, ...nextState.selectedRunIds]))
          : nextState.selectedRunIds,
      };
      setState(nextStateWithContext);
      stateRef.current = nextStateWithContext;

      const prompt = buildAssistantPrompt({
        userMessage,
        session: stateRef.current,
        selectedRunStatus: context.selectedRunStatus,
        selectedRunEvents: context.selectedRunEvents,
        selectedArtifacts: context.selectedArtifacts,
        pendingApproval: context.pendingApproval,
        systemHealth: context.systemHealth,
      });

      const options: AssistantStartTurnOptions = {
        assistantTurnId: turn.id,
        sessionId: stateRef.current.sessionId,
        userMessage,
        compiledPrompt: prompt.compiledPrompt,
        profile: settings.profile,
        ...assistantRuntimeOptionsFromSettings({ ...settings, ...runtimeSettings }),
      };

      try {
        await startAssistantTurn(settings, options);
      } catch (error) {
        const normalized = normalizeAssistantError(error);
        setState((previous) =>
          mapCliAssistantEvent(
            {
              contractVersion: '2.0',
              assistantTurnId: turn.id,
              sessionId: previous.sessionId,
              event: 'error',
              sequence: turn.eventSequence + 1,
              timestampUtc: new Date().toISOString(),
              data: normalized,
            },
            previous,
          ),
        );
      }
    },
    [getContext, settings],
  );

  const newChat = useCallback(() => {
    setState(createAssistantSession());
  }, []);

  const markApprovalDetailLoaded = useCallback((approvalId: string, detail: unknown) => {
    setState((previous) => ({
      ...previous,
      turns: previous.turns.map((turn) => {
        if (turn.assistantMessage.approval?.approvalId !== approvalId) {
          return turn;
        }
        return {
          ...turn,
          assistantMessage: {
            ...turn.assistantMessage,
            approval: {
              ...turn.assistantMessage.approval,
              detailLoaded: true,
              detail,
            },
          },
        };
      }),
    }));
  }, []);

  const appendSystemMessage = useCallback((message: string) => {
    setState((previous) => {
      const active = previous.turns.at(-1);
      if (!active) {
        return previous;
      }
      return {
        ...previous,
        turns: previous.turns.map((turn) =>
          turn.id === active.id
            ? {
                ...turn,
                assistantMessage: {
                  ...turn.assistantMessage,
                  timeline: [
                    ...turn.assistantMessage.timeline,
                    {
                      id: `${turn.id}-system-${Date.now()}`,
                      tone: 'info',
                      title: 'Operator update',
                      subtitle: message,
                      timestampUtc: new Date().toISOString(),
                    },
                  ],
                },
              }
            : turn,
        ),
      };
    });
  }, []);

  return {
    state,
    actions: {
      send,
      newChat,
      applyEvent,
      markApprovalDetailLoaded,
      appendSystemMessage,
    },
  };
}
