import { useCallback, useState } from 'react';

import { BridgeError, planAssistantTask, submitAssistantTask } from '../bridge';
import type { PanelSettings } from '../settings';
import type { AssistantTaskPlan, AssistantTaskSubmissionResult } from './assistantTaskingTypes';

export type AssistantTaskingStatus = 'idle' | 'planning' | 'planned' | 'submitting' | 'submitted' | 'error';

export interface AssistantTaskingError {
  code: string;
  message: string;
}

export interface AssistantTaskingState {
  status: AssistantTaskingStatus;
  plan: AssistantTaskPlan | null;
  submission: AssistantTaskSubmissionResult | null;
  error: AssistantTaskingError | null;
  planTask: (message: string, options?: { operatorId?: string; workspaceId?: string; agentHint?: string }) => Promise<AssistantTaskPlan | null>;
  submitTask: (proposalId: string, confirmPlanHash: string, operatorId: string) => Promise<AssistantTaskSubmissionResult | null>;
  reset: () => void;
}

function toTaskingError(error: unknown): AssistantTaskingError {
  if (error instanceof BridgeError) {
    return {
      code: error.payload.code || 'BRIDGE_ERROR',
      message: error.payload.message || error.message,
    };
  }
  return {
    code: 'ASSISTANT_TASKING_FAILED',
    message: error instanceof Error ? error.message : 'Assistant tasking failed.',
  };
}

export function useAssistantTasking(settings: PanelSettings): AssistantTaskingState {
  const [status, setStatus] = useState<AssistantTaskingStatus>('idle');
  const [plan, setPlan] = useState<AssistantTaskPlan | null>(null);
  const [submission, setSubmission] = useState<AssistantTaskSubmissionResult | null>(null);
  const [error, setError] = useState<AssistantTaskingError | null>(null);

  const planTask = useCallback(
    async (message: string, options?: { operatorId?: string; workspaceId?: string; agentHint?: string }) => {
      setStatus('planning');
      setError(null);
      setSubmission(null);
      try {
        const payload = await planAssistantTask(settings, {
          message,
          operatorId: options?.operatorId,
          workspaceId: options?.workspaceId,
          agentHint: options?.agentHint,
        });
        setPlan(payload);
        setStatus(payload.safeToSubmit || payload.blockedReasons.length === 0 ? 'planned' : 'error');
        return payload;
      } catch (err: unknown) {
        setPlan(null);
        setError(toTaskingError(err));
        setStatus('error');
        return null;
      }
    },
    [settings],
  );

  const submitTask = useCallback(
    async (proposalId: string, confirmPlanHash: string, operatorId: string) => {
      setStatus('submitting');
      setError(null);
      try {
        const payload = await submitAssistantTask(settings, { proposalId, confirmPlanHash, operatorId });
        setSubmission(payload);
        setStatus(payload.status === 'accepted' || payload.status === 'blocked_pending_approval' ? 'submitted' : 'error');
        return payload;
      } catch (err: unknown) {
        setError(toTaskingError(err));
        setStatus('error');
        return null;
      }
    },
    [settings],
  );

  const reset = useCallback(() => {
    setStatus('idle');
    setPlan(null);
    setSubmission(null);
    setError(null);
  }, []);

  return {
    status,
    plan,
    submission,
    error,
    planTask,
    submitTask,
    reset,
  };
}
