import { StatusDot } from '../primitives/StatusDot';

export function AssistantSafetyStrip({
  readOnlyByDefault,
  sensitiveDataNotice,
  dryRunSafe,
}: {
  readOnlyByDefault: string;
  sensitiveDataNotice: string;
  dryRunSafe: string;
}) {
  return (
    <div className="assistant-safety-strip" role="note">
      <span>
        <StatusDot tone="success" /> {readOnlyByDefault}
      </span>
      <span>
        <StatusDot tone="info" /> {sensitiveDataNotice}
      </span>
      <span>
        <StatusDot tone="warning" /> {dryRunSafe}
      </span>
    </div>
  );
}
