import type {
  AssistantFixtureScenario,
  AssistantSessionState,
  AssistantStartTurnResponse,
  AssistantStreamEvent,
} from './assistantTypes';
import { createAssistantSession, createAssistantTurn } from './assistantMappers';

const CONTRACT_VERSION = '2.0';
const FIXTURE_SESSION_ID = 'assistant-preview-session';
const FIXTURE_TURN_ID = 'assistant-preview-turn';

export function previewAssistantStartTurn(
  assistantTurnId = FIXTURE_TURN_ID,
  sessionId = FIXTURE_SESSION_ID,
): AssistantStartTurnResponse {
  return {
    contractVersion: CONTRACT_VERSION,
    assistantTurnId,
    sessionId,
    processId: null,
    status: 'started',
  };
}

export function previewAssistantEvents(
  assistantTurnId = FIXTURE_TURN_ID,
  sessionId = FIXTURE_SESSION_ID,
): AssistantStreamEvent[] {
  return [
    {
      contractVersion: CONTRACT_VERSION,
      assistantTurnId,
      sessionId,
      event: 'status',
      sequence: 1,
      timestampUtc: '2026-03-08T09:20:00Z',
      data: { phase: 'routing', message: 'Inspecting selected run context' },
    },
    {
      contractVersion: CONTRACT_VERSION,
      assistantTurnId,
      sessionId,
      event: 'token',
      sequence: 2,
      timestampUtc: '2026-03-08T09:20:01Z',
      data: { text: 'The selected run is blocked by an approval gate.' },
    },
    {
      contractVersion: CONTRACT_VERSION,
      assistantTurnId,
      sessionId,
      event: 'approval_pending',
      sequence: 3,
      timestampUtc: '2026-03-08T09:20:02Z',
      data: {
        approval_id: 'apr_20260308_device_action',
        title: 'Click preview form start button',
        risk: 'medium',
      },
    },
  ];
}

function baseState(): AssistantSessionState {
  return createAssistantSession(FIXTURE_SESSION_ID);
}

function runningState(): AssistantSessionState {
  const turn = createAssistantTurn({
    id: FIXTURE_TURN_ID,
    sessionId: FIXTURE_SESSION_ID,
    userMessage: 'Son run hatasını özetle',
    createdAtUtc: '2026-03-08T09:20:00Z',
  });
  turn.status = 'streaming';
  turn.eventSequence = 3;
  turn.assistantMessage.text = 'The selected run is blocked by an approval gate.';
  turn.assistantMessage.timeline = [
    {
      id: 'activity-routing',
      tone: 'info',
      title: 'Routing',
      subtitle: 'Inspecting selected run context',
      timestampUtc: '2026-03-08T09:20:00Z',
    },
    {
      id: 'activity-events',
      tone: 'success',
      title: 'Events loaded',
      subtitle: '8 redacted runtime events are available',
      timestampUtc: '2026-03-08T09:20:01Z',
    },
  ];
  turn.assistantMessage.referencedRuns = [
    {
      id: 'job-ui-preview-cu-1',
      status: 'blocked',
      summary: 'Awaiting operator approval before the next computer-use action.',
    },
  ];

  return {
    ...baseState(),
    turns: [turn],
    activeTurnId: turn.id,
    status: 'streaming',
    selectedRunIds: ['job-ui-preview-cu-1'],
  };
}

function approvalRequiredState(): AssistantSessionState {
  const state = runningState();
  const turn = state.turns[0];
  turn.status = 'awaiting_approval';
  turn.assistantMessage.proposedAction = {
    id: 'click_start_button',
    title: 'Click preview form start button',
    target: 'safari:Aegis Preview Form / #start',
    risk: 'medium',
    dryRunSummary: 'Dry-run verified that the target is visible. Execution remains approval-gated.',
    commandPreview: 'computer-use action click --target #start',
  };
  turn.assistantMessage.approval = {
    approvalId: 'apr_20260308_device_action',
    title: 'Click preview form start button',
    status: 'pending',
    risk: 'medium',
    detailLoaded: true,
  };
  turn.assistantMessage.timeline = [
    ...turn.assistantMessage.timeline,
    {
      id: 'activity-approval',
      tone: 'warning',
      title: 'Approval required',
      subtitle: 'Existing governance lifecycle must approve before execution.',
      timestampUtc: '2026-03-08T09:20:02Z',
    },
  ];

  return {
    ...state,
    status: 'awaiting_approval',
    pendingApprovalId: 'apr_20260308_device_action',
  };
}

export function getAssistantFixture(scenario: AssistantFixtureScenario): AssistantSessionState {
  if (scenario === 'running') {
    return runningState();
  }
  if (scenario === 'approval_required') {
    return approvalRequiredState();
  }
  return baseState();
}
