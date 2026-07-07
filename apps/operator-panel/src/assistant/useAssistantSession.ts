import { useCallback, useEffect, useRef, useState } from 'react';

import {
  cancelAssistantTurn,
  isBridgePreviewMode,
  listenAssistantEvents,
  searchAssistantSystemKnowledge,
  startAssistantTurn,
  submitAssistantTask,
} from '../bridge';
import {
  assistantRuntimeOptionsFromSettings,
  type AssistantRuntimeSettings,
  type PanelSettings,
} from '../settings';
import { buildAssistantPrompt } from './assistantPromptBuilder';
import type { AssistantSystemKnowledgeContext } from './assistantSystemKnowledge';
import { previewAssistantEvents } from './assistantFixtures';
import {
  createAssistantSession,
  createAssistantTurn,
  mapCliAssistantEvent,
  normalizeAssistantError,
  startAssistantTurnLocally,
} from './assistantMappers';
import type {
  AssistantComposerControls,
  AssistantSessionState,
  AssistantStartTurnOptions,
  AssistantStreamEvent,
} from './assistantTypes';

const ASSISTANT_TURN_TIMEOUT_MS = 120_000;

function unavailableSystemKnowledge(message: string): AssistantSystemKnowledgeContext {
  return {
    status: 'unavailable',
    identityBrief:
      'AegisOS/BinLiquid platform usage answers must be grounded in local system knowledge and visible runtime context.',
    answerRules: [
      'Do not guess AegisOS platform behavior without verified local sources.',
      'Tell the operator to rebuild or inspect the local system knowledge index.',
    ],
    sources: [],
    contextText: message,
    omittedSources: [],
    blockingReasons: ['ASSISTANT_KNOWLEDGE_UNAVAILABLE'],
  };
}

export type AssistantContextSnapshot = {
  selectedRunId: string;
  selectedRunStatus: unknown | null;
  selectedRunEvents: unknown[];
  selectedArtifacts: Record<string, unknown>;
  pendingApproval: unknown | null;
  systemHealth: unknown | null;
};

export type AssistantSessionActions = {
  send: (
    message: string,
    runtimeSettings?: AssistantRuntimeSettings,
    controls?: AssistantComposerControls,
  ) => Promise<void>;
  newChat: () => void;
  regenerate: (turnId: string, runtimeSettings?: AssistantRuntimeSettings) => Promise<void>;
  cancel: () => Promise<void>;
  submitTaskProposal: (proposalId: string, confirmPlanHash: string) => Promise<void>;
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
  const timeoutTimersRef = useRef<Map<string, number>>(new Map());

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

  const clearTurnTimeout = useCallback((turnId: string) => {
    const timer = timeoutTimersRef.current.get(turnId);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      timeoutTimersRef.current.delete(turnId);
    }
  }, []);

  const armTurnTimeout = useCallback(
    (turnId: string, sessionId: string) => {
      clearTurnTimeout(turnId);
      const timer = window.setTimeout(() => {
        const current = stateRef.current;
        const turn = current.turns.find((item) => item.id === turnId);
        if (!turn || !['starting', 'streaming'].includes(turn.status)) {
          return;
        }
        applyEvent({
          contractVersion: '2.0',
          assistantTurnId: turnId,
          sessionId,
          event: 'error',
          sequence: turn.eventSequence + 1,
          timestampUtc: new Date().toISOString(),
          data: {
            code: 'ASSISTANT_TIMEOUT',
            message: 'Assistant turn timed out before a final event.',
            retryable: true,
          },
        });
      }, ASSISTANT_TURN_TIMEOUT_MS);
      timeoutTimersRef.current.set(turnId, timer);
    },
    [applyEvent, clearTurnTimeout],
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
      timeoutTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      timeoutTimersRef.current.clear();
      cleanup?.();
    };
  }, [applyEvent]);

  useEffect(() => {
    state.turns.forEach((turn) => {
      if (!['starting', 'streaming'].includes(turn.status)) {
        clearTurnTimeout(turn.id);
      }
    });
  }, [clearTurnTimeout, state.turns]);

  const send = useCallback(
    async (
      message: string,
      runtimeSettings?: AssistantRuntimeSettings,
      controls?: AssistantComposerControls,
    ) => {
      const userMessage = message.trim();
      if (!userMessage || ['starting', 'streaming'].includes(stateRef.current.status)) {
        return;
      }

      const context = getContext();
      const turn = createAssistantTurn({
        sessionId: stateRef.current.sessionId,
        userMessage,
        controls,
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

      let systemKnowledge: AssistantSystemKnowledgeContext;
      try {
        const knowledgeResponse = await searchAssistantSystemKnowledge(settings, userMessage);
        systemKnowledge = knowledgeResponse.context;
        applyEvent({
          contractVersion: '2.0',
          assistantTurnId: turn.id,
          sessionId: stateRef.current.sessionId,
          event: 'knowledge_sources',
          sequence: 0.5,
          timestampUtc: new Date().toISOString(),
          data: {
            status: knowledgeResponse.status,
            intent: knowledgeResponse.intent,
            sources: knowledgeResponse.context.sources.map((source) => ({
              path: source.path,
              heading: source.heading,
              score: source.score,
              snippet: source.snippet,
            })),
            blockingReasons: knowledgeResponse.blockingReasons,
          },
        });
      } catch (error) {
        const normalized = normalizeAssistantError(error);
        systemKnowledge = unavailableSystemKnowledge(
          `Local AegisOS system knowledge is unavailable: ${normalized.code}. Suggested command: uv run binliquid assistant knowledge build --profile enterprise --json`,
        );
      }

      const prompt = buildAssistantPrompt({
        userMessage,
        session: stateRef.current,
        selectedRunStatus: context.selectedRunStatus,
        selectedRunEvents: context.selectedRunEvents,
        selectedArtifacts: context.selectedArtifacts,
        pendingApproval: context.pendingApproval,
        systemHealth: context.systemHealth,
        systemKnowledge,
        controls,
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
        if (isBridgePreviewMode()) {
          previewAssistantEvents(turn.id, stateRef.current.sessionId).forEach(applyEvent);
        } else {
          armTurnTimeout(turn.id, stateRef.current.sessionId);
        }
      } catch (error) {
        const normalized = normalizeAssistantError(error);
        clearTurnTimeout(turn.id);
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
    [applyEvent, armTurnTimeout, clearTurnTimeout, getContext, settings],
  );

  const newChat = useCallback(() => {
    setState(createAssistantSession());
  }, []);

  const regenerate = useCallback(
    async (turnId: string, runtimeSettings?: AssistantRuntimeSettings) => {
      const turn = stateRef.current.turns.find((item) => item.id === turnId);
      if (!turn) {
        return;
      }
      await send(turn.userMessage.text, runtimeSettings, turn.composerControls ?? undefined);
    },
    [send],
  );

  const cancel = useCallback(async () => {
    const active = stateRef.current.turns.find((turn) => turn.id === stateRef.current.activeTurnId);
    if (!active || !['starting', 'streaming'].includes(active.status)) {
      return;
    }
    await cancelAssistantTurn(settings, active.id);
    clearTurnTimeout(active.id);
    applyEvent({
      contractVersion: '2.0',
      assistantTurnId: active.id,
      sessionId: stateRef.current.sessionId,
      event: 'cancelled',
      sequence: 9_000_000_000,
      timestampUtc: new Date().toISOString(),
      data: {
        message: 'Assistant turn cancelled by operator.',
      },
    });
  }, [applyEvent, clearTurnTimeout, settings]);

  const submitTaskProposal = useCallback(
    async (proposalId: string, confirmPlanHash: string) => {
      const current = stateRef.current;
      const turn = current.turns
        .slice()
        .reverse()
        .find((item) => item.assistantMessage.taskPlan?.proposalId === proposalId);
      if (!turn || !confirmPlanHash || !settings.operatorId.trim()) {
        return;
      }
      try {
        const submission = await submitAssistantTask(settings, {
          proposalId,
          confirmPlanHash,
          operatorId: settings.operatorId.trim(),
        });
        applyEvent({
          contractVersion: '2.0',
          assistantTurnId: turn.id,
          sessionId: current.sessionId,
          event: 'task_submission',
          sequence: turn.eventSequence + 1,
          timestampUtc: new Date().toISOString(),
          data: submission,
        });
      } catch (error) {
        const normalized = normalizeAssistantError(error);
        applyEvent({
          contractVersion: '2.0',
          assistantTurnId: turn.id,
          sessionId: current.sessionId,
          event: 'error',
          sequence: turn.eventSequence + 1,
          timestampUtc: new Date().toISOString(),
          data: normalized,
        });
      }
    },
    [applyEvent, settings],
  );

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
      regenerate,
      cancel,
      submitTaskProposal,
      applyEvent,
      markApprovalDetailLoaded,
      appendSystemMessage,
    },
  };
}
