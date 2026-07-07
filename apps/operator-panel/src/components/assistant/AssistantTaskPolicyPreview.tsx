import type { AssistantTaskPolicyPreview as AssistantTaskPolicyPreviewModel } from '../../assistant/assistantTaskingTypes';
import { Badge, type BadgeTone } from '../primitives/Badge';
import { Icon } from '../primitives/Icon';

function decisionTone(decision: AssistantTaskPolicyPreviewModel['decision']): BadgeTone {
  if (decision === 'allow') {
    return 'success';
  }
  if (decision === 'deny') {
    return 'error';
  }
  return 'warning';
}

export function AssistantTaskPolicyPreview({ policy }: { policy: AssistantTaskPolicyPreviewModel }) {
  return (
    <div className="assistant-task-policy-preview">
      <div>
        <span>
          <Icon name="policy" /> Policy
        </span>
        <Badge tone={decisionTone(policy.decision)}>{policy.decision.replaceAll('_', ' ')}</Badge>
      </div>
      <dl>
        <div>
          <dt>Risk</dt>
          <dd>{policy.riskClass.replaceAll('_', ' ')}</dd>
        </div>
        <div>
          <dt>Approval</dt>
          <dd>{policy.approvalRequired ? 'required' : 'not required'}</dd>
        </div>
        <div>
          <dt>Reason</dt>
          <dd>{policy.reasonCode}</dd>
        </div>
      </dl>
      {policy.blockedReasons.length > 0 ? (
        <ul>
          {policy.blockedReasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
