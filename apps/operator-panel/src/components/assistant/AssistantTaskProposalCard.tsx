import type { AssistantTaskPlan } from '../../assistant/assistantTaskingTypes';
import { Badge, type BadgeTone } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { AssistantAgentCandidateList } from './AssistantAgentCandidateList';
import { AssistantTaskPolicyPreview } from './AssistantTaskPolicyPreview';

function statusTone(plan: AssistantTaskPlan): BadgeTone {
  if (plan.status === 'planned' && plan.safeToSubmit) {
    return 'success';
  }
  if (plan.policyPreview.decision === 'deny') {
    return 'error';
  }
  return 'warning';
}

function shortHash(planHash: string): string {
  if (!planHash.startsWith('sha256:') || planHash.length < 18) {
    return planHash || 'missing';
  }
  return `${planHash.slice(0, 14)}...${planHash.slice(-8)}`;
}

export function AssistantTaskProposalCard({
  plan,
  onSubmit,
}: {
  plan: AssistantTaskPlan;
  onSubmit?: (proposalId: string, confirmPlanHash: string) => void;
}) {
  const submitDisabled = !plan.safeToSubmit || !plan.planHash || plan.submitMode !== 'proposal_first';
  const disabledReason = !plan.safeToSubmit
    ? 'Policy preview blocked submission.'
    : !plan.planHash
      ? 'Plan hash is required before submit.'
      : plan.submitMode !== 'proposal_first'
        ? 'Submit mode is disabled for this proposal.'
        : '';
  return (
    <Card className="assistant-task-proposal-card">
      <div className="assistant-card-head">
        <span className="assistant-card-label">Governed task proposal</span>
        <Badge tone={statusTone(plan)}>{plan.status.replaceAll('_', ' ')}</Badge>
      </div>
      <div className="assistant-task-title">
        <Icon name="shield" />
        <span>
          <strong>{plan.taskSummary}</strong>
          <em>{plan.proposalId}</em>
        </span>
      </div>
      <AssistantTaskPolicyPreview policy={plan.policyPreview} />
      <dl className="assistant-task-metrics">
        <div>
          <dt>Plan hash</dt>
          <dd>{shortHash(plan.planHash)}</dd>
        </div>
        <div>
          <dt>Submit mode</dt>
          <dd>{plan.submitMode.replaceAll('_', ' ')}</dd>
        </div>
        <div>
          <dt>Evidence</dt>
          <dd>{plan.evidenceExpectation.mode.replaceAll('_', ' ')}</dd>
        </div>
      </dl>
      <AssistantAgentCandidateList agents={plan.candidateAgents} />
      {plan.blockedReasons.length > 0 ? (
        <ul className="assistant-task-blockers">
          {plan.blockedReasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
      <div className="assistant-task-actions">
        <Button
          variant="primary"
          icon={<Icon name="send" />}
          disabled={submitDisabled || !onSubmit}
          onClick={() => onSubmit?.(plan.proposalId, plan.planHash)}
        >
          Submit with plan hash
        </Button>
        <span>{submitDisabled ? disabledReason : `confirmPlanHash ${shortHash(plan.planHash)}`}</span>
      </div>
    </Card>
  );
}
