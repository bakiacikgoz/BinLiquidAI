import type { AssistantTurn } from '../../assistant/assistantTypes';
import { AssistantMessage } from './AssistantMessage';

export function AssistantTranscript({
  turns,
  approvalDisabled,
  approvalDisabledReason,
  emptyRunLabel,
  debugRawEnabled,
  onReviewApproval,
  onApprove,
  onReject,
  onExecute,
}: {
  turns: AssistantTurn[];
  approvalDisabled: boolean;
  approvalDisabledReason: string;
  emptyRunLabel: string;
  debugRawEnabled: boolean;
  onReviewApproval: (approvalId: string) => void;
  onApprove: (approvalId: string) => void;
  onReject: (approvalId: string) => void;
  onExecute: (approvalId: string) => void;
}) {
  return (
    <div className="assistant-transcript" role="log" aria-live="polite">
      {turns.map((turn) => (
        <AssistantMessage
          key={turn.id}
          turn={turn}
          approvalDisabled={approvalDisabled}
          approvalDisabledReason={approvalDisabledReason}
          emptyRunLabel={emptyRunLabel}
          debugRawEnabled={debugRawEnabled}
          onReviewApproval={onReviewApproval}
          onApprove={onApprove}
          onReject={onReject}
          onExecute={onExecute}
        />
      ))}
    </div>
  );
}
