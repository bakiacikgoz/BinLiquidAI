import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';
import { MissionObjectiveCard } from './MissionObjectiveCard';
import { RunStatusCard } from './RunStatusCard';
import { StageProgress, type MissionStageKey } from './StageProgress';
import { LiveAgentActivity, type ActivityItem } from './LiveAgentActivity';
import { ApprovalGateCard } from './ApprovalGateCard';
import { RuntimeSummaryCard, type RuntimeSummaryItem } from './RuntimeSummaryCard';
import { SessionEventsCard, type SessionEventItem } from './SessionEventsCard';
import type { ComputerUseCapabilityResolution } from '../../capabilities';

export type RunOption = {
  id: string;
  label: string;
};

export type MissionControlViewProps = {
  runOptions: RunOption[];
  selectedRunId: string;
  sessionId: string;
  sessionStatus: string;
  objective: string;
  priority: string;
  targetType: string;
  statusCode: string;
  statusError: string;
  stageLabel: string;
  stageKey: MissionStageKey;
  startedAt: string;
  duration: string;
  progress: number;
  activityItems: ActivityItem[];
  sessionEvents: SessionEventItem[];
  runtimeSummary: RuntimeSummaryItem[];
  rawSummary: unknown;
  computerUseCapabilityResolution?: ComputerUseCapabilityResolution | null;
  debugRawEnabled: boolean;
  hasApproval: boolean;
  approvalLabel: string;
  approvalDisabled: boolean;
  approvalDisabledReason: string;
  onSelectRun: (runId: string) => void;
  onRawJsonRequested: () => boolean;
  onApprove: () => void;
  onEditApproval: () => void;
  onReject: () => void;
};

export function MissionControlView({
  runOptions,
  selectedRunId,
  sessionId,
  sessionStatus,
  objective,
  priority,
  targetType,
  statusCode,
  statusError,
  stageLabel,
  stageKey,
  startedAt,
  duration,
  progress,
  activityItems,
  sessionEvents,
  runtimeSummary,
  rawSummary,
  computerUseCapabilityResolution,
  debugRawEnabled,
  hasApproval,
  approvalLabel,
  approvalDisabled,
  approvalDisabledReason,
  onSelectRun,
  onRawJsonRequested,
  onApprove,
  onEditApproval,
  onReject,
}: MissionControlViewProps) {
  return (
    <section className="mission-control-view">
      <div className="mission-title-row">
        <div className="mission-title">
          <h1>Mission Control</h1>
          <span>
            <StatusDot tone="success" pulse /> CANLI
          </span>
        </div>
      </div>

      <div className="mission-control-selectors">
        <label className="mission-selector">
          <span>Çalıştırma Seç</span>
          <select value={selectedRunId} onChange={(event) => onSelectRun(event.target.value)}>
            {runOptions.length > 0 ? (
              runOptions.map((run) => (
                <option value={run.id} key={run.id}>
                  {run.label}
                </option>
              ))
            ) : (
              <option value="">Çalıştırma seçin</option>
            )}
          </select>
          <Icon name="chevron" />
        </label>
        <label className="mission-selector">
          <span>Oturum</span>
          <strong>{sessionId}</strong>
          <em>
            <StatusDot tone="success" /> {sessionStatus}
          </em>
          <Icon name="chevron" />
        </label>
      </div>

      <MissionObjectiveCard objective={objective} priority={priority} targetType={targetType} />

      <div className="mission-status-grid">
        <RunStatusCard
          status={statusCode}
          error={statusError}
          stage={stageLabel}
          startedAt={startedAt}
          duration={duration}
          progress={progress}
        />
        <Card className="stage-progress-card">
          <span className="mc-kicker">AŞAMA İLERLEMESİ</span>
          <StageProgress currentStage={stageKey} />
        </Card>
      </div>

      <div className="mission-middle-grid">
        <LiveAgentActivity items={activityItems} />
        <ApprovalGateCard
          hasApproval={hasApproval}
          disabled={approvalDisabled}
          disabledReason={approvalDisabledReason}
          approvalLabel={approvalLabel}
          onApprove={onApprove}
          onEdit={onEditApproval}
          onReject={onReject}
        />
      </div>

      <div className="mission-bottom-grid">
        <SessionEventsCard items={sessionEvents} />
        <RuntimeSummaryCard
          debugRawEnabled={debugRawEnabled}
          items={runtimeSummary}
          rawJson={rawSummary}
          computerUseCapabilityResolution={computerUseCapabilityResolution}
          onRawJsonRequested={onRawJsonRequested}
        />
      </div>
    </section>
  );
}
