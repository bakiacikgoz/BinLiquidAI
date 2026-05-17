import type { ReactNode } from 'react';

import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';
import type { PendingApprovalSummary, SystemHealthSummary, SystemHealthStatus } from '../shell/RightRail';

function healthTone(health: SystemHealthStatus): 'success' | 'warning' | 'error' | 'info' {
  if (health === 'Healthy') {
    return 'success';
  }
  if (health === 'Blocked') {
    return 'error';
  }
  if (health === 'Degraded') {
    return 'warning';
  }
  return 'info';
}

function statusTone(status: AssistantSessionState['status']): 'success' | 'warning' | 'error' | 'info' {
  if (status === 'failed') {
    return 'error';
  }
  if (status === 'awaiting_approval') {
    return 'warning';
  }
  if (status === 'completed') {
    return 'success';
  }
  return 'info';
}

function statusLabel(value: string): string {
  return value.replaceAll('_', ' ');
}

function RailSection({
  title,
  action,
  children,
  className = '',
}: {
  title: string;
  action?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={`assistant-rail-card ${className}`.trim()}>
      <div className="assistant-rail-card-head">
        <span>{title}</span>
        {action ? <button type="button">{action}</button> : null}
      </div>
      {children}
    </Card>
  );
}

export function AssistantRightRail({
  state,
  systemHealth,
  pendingApprovals,
  selectedRunId,
  onRefreshContext,
  onViewApprovals,
  onViewRuns,
}: {
  state: AssistantSessionState;
  systemHealth: SystemHealthSummary;
  pendingApprovals: PendingApprovalSummary[];
  selectedRunId: string;
  onRefreshContext: () => void;
  onViewApprovals: () => void;
  onViewRuns: () => void;
}) {
  const activeTurn = state.turns.find((turn) => turn.id === state.activeTurnId) ?? state.turns.at(-1);
  const mode = state.status === 'awaiting_approval' ? 'approval' : state.turns.length > 0 ? 'transcript' : 'welcome';
  const healthBadgeTone = healthTone(systemHealth.health);
  const approval = pendingApprovals[0];
  const referencedRuns = state.selectedRunIds.length > 0 ? state.selectedRunIds : selectedRunId ? [selectedRunId] : [];

  return (
    <aside className={`assistant-right-rail assistant-right-rail-${mode}`} aria-label="Assistant context rail">
      {mode === 'welcome' ? (
        <>
          <RailSection title="System Health">
            <div className="assistant-health-summary">
              <p>
                <StatusDot tone={healthBadgeTone} /> All systems operational
              </p>
              <dl>
                <div>
                  <dt>Runtime</dt>
                  <dd className="assistant-success-value">{systemHealth.health}</dd>
                </div>
                <div>
                  <dt>Approvals</dt>
                  <dd className="assistant-success-value">{pendingApprovals.length > 0 ? 'On track' : 'Clear'}</dd>
                </div>
                <div>
                  <dt>Integrations</dt>
                  <dd className="assistant-success-value">{systemHealth.networkStatus ?? 'Connected'}</dd>
                </div>
                <div>
                  <dt>Policy Compliance</dt>
                  <dd className="assistant-success-value">98%</dd>
                </div>
              </dl>
              <Button variant="ghost" onClick={onRefreshContext}>
                View System Status
              </Button>
            </div>
          </RailSection>

          <RailSection title="Recent Sessions" action="View all">
            <div className="assistant-rail-list">
              {['Investigate run_20260308_0910', 'Error spike in payment-service', 'Draft remediation plan'].map(
                (item) => (
                  <button type="button" key={item} onClick={onViewRuns}>
                    <Icon name="logs" />
                    <span>
                      <strong>{item}</strong>
                      <em>8 Mar 2026 · 12:10</em>
                    </span>
                    <StatusDot tone="success" />
                  </button>
                ),
              )}
            </div>
          </RailSection>

          <RailSection title="Quick Actions">
            <div className="assistant-quick-actions">
              <Button icon={<Icon name="approval" />} variant="ghost" onClick={onRefreshContext}>
                Create a new plan
              </Button>
              <Button icon={<Icon name="gauge" />} variant="ghost" onClick={onViewRuns}>
                Run an inspection
              </Button>
              <Button icon={<Icon name="shield" />} variant="ghost" onClick={onRefreshContext}>
                Check compliance status
              </Button>
              <Button icon={<Icon name="check" />} variant="ghost" onClick={onViewApprovals}>
                Open approvals queue
              </Button>
            </div>
          </RailSection>

          <RailSection title="Safe Execution Preview">
            <div className="assistant-execution-preview">
              <p>Assistant can propose commands and config changes. Execution requires approval and is always auditable.</p>
              <div>
                <span>
                  <Icon name="sparkle" />
                  Propose
                </span>
                <span>
                  <Icon name="eye" />
                  Review
                </span>
                <span>
                  <Icon name="check" />
                  Approve
                </span>
                <span>
                  <Icon name="play" />
                  Execute
                </span>
              </div>
            </div>
          </RailSection>
        </>
      ) : null}

      {mode === 'transcript' ? (
        <>
          <RailSection title="Active Session">
            <Badge tone={statusTone(state.status)}>{statusLabel(state.status)}</Badge>
            <dl className="assistant-rail-dl">
              <div>
                <dt>Session ID</dt>
                <dd>{state.sessionId}</dd>
              </div>
              <div>
                <dt>Run ID</dt>
                <dd>{selectedRunId || '-'}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{activeTurn?.status ?? state.status}</dd>
              </div>
              <div>
                <dt>Duration</dt>
                <dd>00:03:18</dd>
              </div>
            </dl>
            <Button variant="ghost" onClick={onViewRuns}>
              Open in Mission Control
            </Button>
          </RailSection>

          <RailSection title="Referenced Runs" action="View all">
            <div className="assistant-rail-list assistant-run-list">
              {referencedRuns.map((runId, index) => (
                <button type="button" key={runId} onClick={onViewRuns}>
                  <Icon name="target" />
                  <span>
                    <strong>{runId}</strong>
                    <em>{index === 0 ? 'Blocked' : 'Succeeded'}</em>
                  </span>
                  <time>{index === 0 ? '12:10' : 'Yesterday'}</time>
                </button>
              ))}
            </div>
          </RailSection>

          <RailSection title="System Health">
            <div className="assistant-health-summary compact">
              <p>
                <StatusDot tone={healthBadgeTone} /> All systems operational
              </p>
              <dl>
                <div>
                  <dt>Runtime</dt>
                  <dd>{systemHealth.health}</dd>
                </div>
                <div>
                  <dt>Contract</dt>
                  <dd>{systemHealth.contractVersion}</dd>
                </div>
              </dl>
            </div>
          </RailSection>

          <RailSection title="Related Artifact">
            <div className="assistant-artifact-card">
              <Icon name="terminal" />
              <span>
                <strong>Run Summary</strong>
                <em>{selectedRunId || 'No selected run'}</em>
              </span>
              <Button variant="ghost" onClick={onViewRuns}>
                Open artifact
              </Button>
            </div>
          </RailSection>
        </>
      ) : null}

      {mode === 'approval' ? (
        <>
          <RailSection title="Approval Queue" action="View all">
            <div className="assistant-approval-ticket">
              <strong>{approval?.title ?? 'Restart operator queue deployment'}</strong>
              <span>{approval?.subtitle ?? selectedRunId}</span>
              <em>Waiting for your approval</em>
              <div>
                <Button icon={<Icon name="eye" />} variant="ghost" onClick={onViewApprovals}>
                  Review
                </Button>
                <Button icon={<Icon name="check" />} variant="primary" onClick={onViewApprovals}>
                  Approve
                </Button>
              </div>
            </div>
          </RailSection>

          <RailSection title="Execution Preview (Dry Run)">
            <Badge tone="success">Safe</Badge>
            <div className="assistant-diff-preview" aria-label="Dry run diff preview">
              <span>1 | # Dry run: rollout restart</span>
              <span className="diff-remove">2 | - replicas: 3</span>
              <span className="diff-add">3 | + replicas: 3</span>
              <span>4 | ~ pod template hash changed</span>
              <span>5 | ~ restart strategy: RollingUpdate</span>
            </div>
            <Button variant="ghost" onClick={onViewRuns}>
              View Full Diff
            </Button>
          </RailSection>

          <RailSection title="Policy Checks">
            <div className="assistant-policy-checks">
              {['Change is permitted by active policies', 'Target is in approved namespace', 'Risk level accepted for this operation'].map(
                (item) => (
                  <span key={item}>
                    <StatusDot tone="success" /> {item}
                  </span>
                ),
              )}
            </div>
          </RailSection>

          <RailSection title="Recent Activity" action="View all">
            <div className="assistant-rail-list">
              {['Health check failed: operator queue', 'Auto-diagnosis completed', 'Run initiated by user'].map(
                (item, index) => (
                  <button type="button" key={item} onClick={onViewRuns}>
                    <StatusDot tone={index === 0 ? 'error' : index === 1 ? 'info' : 'success'} />
                    <span>
                      <strong>{item}</strong>
                      <em>{selectedRunId || 'run_20260308_0910'}</em>
                    </span>
                    <time>12:08</time>
                  </button>
                ),
              )}
            </div>
          </RailSection>
        </>
      ) : null}
    </aside>
  );
}
