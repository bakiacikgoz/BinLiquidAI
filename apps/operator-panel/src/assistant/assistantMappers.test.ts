import { describe, expect, it } from 'vitest';

import {
  createAssistantSession,
  createAssistantTurn,
  extractApprovalIdFromEvent,
  mapCliAssistantEvent,
  normalizeAssistantStreamEvent,
  startAssistantTurnLocally,
} from './assistantMappers';

function started() {
  const session = createAssistantSession('session-test');
  const turn = createAssistantTurn({
    id: 'turn-test',
    sessionId: session.sessionId,
    userMessage: 'inspect failed run',
    createdAtUtc: '2026-03-08T09:00:00Z',
  });
  return startAssistantTurnLocally(session, turn);
}

describe('assistant mappers', () => {
  it.each([
    ['missing', undefined],
    ['former', ['2', '0'].join('.')],
  ])('drops %s contract versions without mutating state', (_label, contractVersion) => {
    const state = started();
    const rawEvent = {
      ...(contractVersion ? { contractVersion } : {}),
      assistantTurnId: 'turn-test',
      sessionId: 'session-test',
      event: 'token',
      sequence: 1,
      timestampUtc: '2026-03-08T09:00:01Z',
      data: { text: 'must not be appended' },
    };

    expect(normalizeAssistantStreamEvent(rawEvent)).toBeNull();
    expect(mapCliAssistantEvent(rawEvent as never, state)).toBe(state);
    expect(state.turns[0].assistantMessage.text).toBe('');
    expect(state.turns[0].eventSequence).toBe(0);
  });

  it('appends token events and ignores duplicate sequences', () => {
    const state = started();
    const withToken = mapCliAssistantEvent(
      {
        contractVersion: '3.0',
        assistantTurnId: 'turn-test',
        sessionId: 'session-test',
        event: 'token',
        sequence: 1,
        timestampUtc: '2026-03-08T09:00:01Z',
        data: { text: 'Hello' },
      },
      state,
    );
    const duplicate = mapCliAssistantEvent(
      {
        contractVersion: '3.0',
        assistantTurnId: 'turn-test',
        sessionId: 'session-test',
        event: 'token',
        sequence: 1,
        timestampUtc: '2026-03-08T09:00:01Z',
        data: { text: ' again' },
      },
      withToken,
    );

    expect(duplicate.turns[0].assistantMessage.text).toBe('Hello');
  });

  it('marks final events as completed with metrics', () => {
    const completed = mapCliAssistantEvent(
      {
        contractVersion: '3.0',
        assistantTurnId: 'turn-test',
        sessionId: 'session-test',
        event: 'final',
        sequence: 1,
        timestampUtc: '2026-03-08T09:00:02Z',
        data: { final_text: 'Done', trace_id: 'trace-1', used_path: 'llm_only' },
      },
      started(),
    );

    expect(completed.status).toBe('completed');
    expect(completed.activeTurnId).toBeNull();
    expect(completed.turns[0].assistantMessage.text).toBe('Done');
    expect(completed.turns[0].assistantMessage.metrics?.traceId).toBe('trace-1');
  });

  it('maps approval pending events into guarded approval state', () => {
    const event = {
      contractVersion: '3.0',
      assistantTurnId: 'turn-test',
      sessionId: 'session-test',
      event: 'approval_pending' as const,
      sequence: 1,
      timestampUtc: '2026-03-08T09:00:03Z',
      data: { approval_id: 'apr_1', title: 'Run action', risk: 'medium' },
    };
    const awaitingApproval = mapCliAssistantEvent(event, started());

    expect(extractApprovalIdFromEvent(event)).toBe('apr_1');
    expect(awaitingApproval.status).toBe('awaiting_approval');
    expect(awaitingApproval.pendingApprovalId).toBe('apr_1');
    expect(awaitingApproval.turns[0].assistantMessage.approval?.detailLoaded).toBe(false);
  });

  it('keeps warning events non-blocking', () => {
    const warned = mapCliAssistantEvent(
      {
        contractVersion: '3.0',
        assistantTurnId: 'turn-test',
        sessionId: 'session-test',
        event: 'warning',
        sequence: 1,
        timestampUtc: '2026-03-08T09:00:04Z',
        data: { message: 'ignored malformed stdout line' },
      },
      started(),
    );

    expect(warned.status).toBe('starting');
    expect(warned.turns[0].assistantMessage.warning).toBe('ignored malformed stdout line');
  });

  it('maps cancelled events into a non-error terminal state', () => {
    const cancelled = mapCliAssistantEvent(
      {
        contractVersion: '3.0',
        assistantTurnId: 'turn-test',
        sessionId: 'session-test',
        event: 'cancelled',
        sequence: 1,
        timestampUtc: '2026-03-08T09:00:05Z',
        data: { message: 'Assistant turn cancelled by operator.' },
      },
      started(),
    );

    expect(cancelled.status).toBe('cancelled');
    expect(cancelled.activeTurnId).toBeNull();
    expect(cancelled.error).toBeNull();
    expect(cancelled.turns[0].status).toBe('cancelled');
  });
});
