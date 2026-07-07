import type { ReactNode } from 'react';

import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { assistantUiText, translateAssistantText, type UiLocale } from '../../i18n';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';
import type { PendingApprovalSummary, SystemHealthSummary, SystemHealthStatus } from '../shell/RightRail';
import { AssistantKnowledgeSourcesCard } from './AssistantKnowledgeSourcesCard';

export type AssistantRuntimeSummary = {
  selectedProvider: string;
  selectedModel: string;
  selectedFallbackProvider: string;
  selectedHfModelId: string;
  effectiveProvider: string;
  effectiveModel: string;
  effectiveHfModelId: string;
};

export type AssistantRailSession = {
  id: string;
  title: string;
  status: string;
  timestamp: string;
};

export type AssistantComplianceSummary = {
  label: string;
  tone: 'success' | 'warning' | 'error' | 'info';
};

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

function formatDuration(startedAtUtc?: string, completedAtUtc?: string | null): string {
  if (!startedAtUtc) {
    return '-';
  }
  const start = new Date(startedAtUtc).getTime();
  const end = completedAtUtc ? new Date(completedAtUtc).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) {
    return '-';
  }
  const totalSeconds = Math.floor((end - start) / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function RailSection({
  title,
  action,
  onAction,
  children,
  className = '',
}: {
  title: string;
  action?: string;
  onAction?: () => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={`assistant-rail-card ${className}`.trim()}>
      <div className="assistant-rail-card-head">
        <span>{title}</span>
        {action ? (
          <button
            type="button"
            disabled={!onAction}
            title={!onAction ? 'Action is not available in this context' : undefined}
            onClick={onAction}
          >
            {action}
          </button>
        ) : null}
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
  runtimeSummary,
  recentSessions,
  complianceSummary,
  relatedArtifacts,
  onRefreshContext,
  onViewApprovals,
  onViewRuns,
  locale = 'en',
}: {
  state: AssistantSessionState;
  systemHealth: SystemHealthSummary;
  pendingApprovals: PendingApprovalSummary[];
  selectedRunId: string;
  runtimeSummary: AssistantRuntimeSummary;
  recentSessions: AssistantRailSession[];
  complianceSummary: AssistantComplianceSummary;
  relatedArtifacts: Array<{ name: string; path?: string; summary?: string }>;
  onRefreshContext: () => void;
  onViewApprovals: () => void;
  onViewRuns: () => void;
  locale?: UiLocale;
}) {
  const text = assistantUiText[locale];
  const activeTurn = state.turns.find((turn) => turn.id === state.activeTurnId) ?? state.turns.at(-1);
  const mode = state.status === 'awaiting_approval' ? 'approval' : state.turns.length > 0 ? 'transcript' : 'welcome';
  const healthBadgeTone = healthTone(systemHealth.health);
  const approval = pendingApprovals[0];
  const referencedRuns = state.selectedRunIds.length > 0 ? state.selectedRunIds : selectedRunId ? [selectedRunId] : [];
  const displayedArtifacts = state.referencedArtifacts.length > 0 ? state.referencedArtifacts : relatedArtifacts;

  return (
    <aside className={`assistant-right-rail assistant-right-rail-${mode}`} aria-label="Assistant context rail">
      <RailSection title={text.assistantRuntime}>
        <dl className="assistant-rail-dl assistant-runtime-dl">
          <div>
            <dt>{text.selected}</dt>
            <dd>
              {runtimeSummary.selectedProvider} / {runtimeSummary.selectedModel}
            </dd>
          </div>
          <div>
            <dt>{text.fallback}</dt>
            <dd>{runtimeSummary.selectedFallbackProvider}</dd>
          </div>
          <div>
            <dt>{text.hfModel}</dt>
            <dd>{runtimeSummary.selectedHfModelId}</dd>
          </div>
          <div>
            <dt>{text.effective}</dt>
            <dd>
              {runtimeSummary.effectiveProvider} / {runtimeSummary.effectiveModel}
            </dd>
          </div>
          <div>
            <dt>{text.effectiveHf}</dt>
            <dd>{runtimeSummary.effectiveHfModelId}</dd>
          </div>
        </dl>
      </RailSection>
      {mode === 'welcome' ? (
        <>
          <RailSection title={text.systemHealth}>
            <div className="assistant-health-summary">
              <p>
                <StatusDot tone={healthBadgeTone} /> {text.allSystemsOperational}
              </p>
              <dl>
                <div>
                  <dt>{text.runtimeStatus}</dt>
                  <dd className="assistant-success-value">{translateAssistantText(systemHealth.health, locale)}</dd>
                </div>
                <div>
                  <dt>{text.approvals}</dt>
                  <dd className="assistant-success-value">
                    {pendingApprovals.length > 0
                      ? translateAssistantText('On track', locale)
                      : translateAssistantText('Clear', locale)}
                  </dd>
                </div>
                <div>
                  <dt>{text.integrations}</dt>
                  <dd className="assistant-success-value">{translateAssistantText(systemHealth.networkStatus ?? 'Connected', locale)}</dd>
                </div>
                <div>
                  <dt>{text.policyCompliance}</dt>
                  <dd className={`assistant-${complianceSummary.tone}-value`}>
                    {translateAssistantText(complianceSummary.label, locale)}
                  </dd>
                </div>
              </dl>
              <Button variant="ghost" onClick={onRefreshContext}>
                {text.viewSystemStatus}
              </Button>
            </div>
          </RailSection>

          <RailSection title={text.recentSessions} action={text.viewAll} onAction={onViewRuns}>
            <div className="assistant-rail-list">
              {recentSessions.length > 0 ? (
                recentSessions.map((item) => (
                  <button type="button" key={item.id} onClick={onViewRuns}>
                    <Icon name="logs" />
                    <span>
                      <strong>{item.title}</strong>
                      <em>{translateAssistantText(item.status, locale)}</em>
                    </span>
                    <time>{item.timestamp || '-'}</time>
                  </button>
                ))
              ) : (
                <p className="assistant-empty-state">{text.noRecentSessionsAvailable}</p>
              )}
            </div>
          </RailSection>

          <RailSection title={text.quickActions}>
            <div className="assistant-quick-actions">
              <Button icon={<Icon name="approval" />} variant="ghost" onClick={onRefreshContext}>
                {text.createNewPlan}
              </Button>
              <Button icon={<Icon name="gauge" />} variant="ghost" onClick={onViewRuns}>
                {text.runInspection}
              </Button>
              <Button icon={<Icon name="shield" />} variant="ghost" onClick={onRefreshContext}>
                {text.checkComplianceStatus}
              </Button>
              <Button icon={<Icon name="check" />} variant="ghost" onClick={onViewApprovals}>
                {text.openApprovalsQueue}
              </Button>
            </div>
          </RailSection>

          <RailSection title={text.safeExecutionPreview}>
            <div className="assistant-execution-preview">
              <p>
                {locale === 'tr'
                  ? 'Asistan komut ve config değişikliği önerebilir. Yürütme onay gerektirir ve her zaman denetlenebilir.'
                  : 'Assistant can propose commands and config changes. Execution requires approval and is always auditable.'}
              </p>
              <div>
                <span>
                  <Icon name="sparkle" />
                  {locale === 'tr' ? 'Öner' : 'Propose'}
                </span>
                <span>
                  <Icon name="eye" />
                  {text.review}
                </span>
                <span>
                  <Icon name="check" />
                  {text.approve}
                </span>
                <span>
                  <Icon name="play" />
                  {text.execute}
                </span>
              </div>
            </div>
          </RailSection>
        </>
      ) : null}

      {mode === 'transcript' ? (
        <>
          <RailSection title={text.activeSession}>
            <Badge tone={statusTone(state.status)}>{translateAssistantText(statusLabel(state.status), locale)}</Badge>
            <dl className="assistant-rail-dl">
              <div>
                <dt>{text.sessionId}</dt>
                <dd>{state.sessionId}</dd>
              </div>
              <div>
                <dt>{text.runId}</dt>
                <dd>{selectedRunId || '-'}</dd>
              </div>
              <div>
                <dt>{text.status}</dt>
                <dd>{translateAssistantText(activeTurn?.status ?? state.status, locale)}</dd>
              </div>
              <div>
                <dt>{text.duration}</dt>
                <dd>{formatDuration(activeTurn?.startedAtUtc, activeTurn?.completedAtUtc)}</dd>
              </div>
            </dl>
            <Button variant="ghost" onClick={onViewRuns}>
              {text.openInMissionControl}
            </Button>
          </RailSection>

          <RailSection title={text.referencedRuns} action={text.viewAll} onAction={onViewRuns}>
            <div className="assistant-rail-list assistant-run-list">
              {referencedRuns.map((runId, index) => (
                <button type="button" key={runId} onClick={onViewRuns}>
                  <Icon name="target" />
                  <span>
                    <strong>{runId}</strong>
                    <em>{index === 0 ? text.blocked : translateAssistantText('Succeeded', locale)}</em>
                  </span>
                  <time>{index === 0 ? '12:10' : translateAssistantText('Yesterday', locale)}</time>
                </button>
              ))}
            </div>
          </RailSection>

          <RailSection title={text.systemHealth}>
            <div className="assistant-health-summary compact">
              <p>
                <StatusDot tone={healthBadgeTone} /> {text.allSystemsOperational}
              </p>
              <dl>
                <div>
                  <dt>{text.runtimeStatus}</dt>
                  <dd>{translateAssistantText(systemHealth.health, locale)}</dd>
                </div>
                <div>
                  <dt>{text.contract}</dt>
                  <dd>{systemHealth.contractVersion}</dd>
                </div>
              </dl>
            </div>
          </RailSection>

          <AssistantKnowledgeSourcesCard sources={activeTurn?.assistantMessage.knowledgeSources ?? []} />

          <RailSection title={text.relatedArtifact}>
            {displayedArtifacts.length > 0 ? (
              displayedArtifacts.slice(0, 3).map((artifact) => (
                <div className="assistant-artifact-card" key={`${artifact.name}:${artifact.path ?? ''}`}>
                  <Icon name="terminal" />
                  <span>
                    <strong>{artifact.name}</strong>
                    <em>{translateAssistantText(artifact.summary || artifact.path || selectedRunId || 'No selected run', locale)}</em>
                  </span>
                  <Button variant="ghost" onClick={onViewRuns}>
                    {text.openArtifact}
                  </Button>
                </div>
              ))
            ) : (
              <p className="assistant-empty-state">{text.noRelatedArtifact}</p>
            )}
          </RailSection>
        </>
      ) : null}

      {mode === 'approval' ? (
        <>
          <RailSection title={text.approvalQueue} action={text.viewAll} onAction={onViewApprovals}>
            <div className="assistant-approval-ticket">
              <strong>{translateAssistantText(approval?.title ?? 'Restart operator queue deployment', locale)}</strong>
              <span>{approval?.subtitle ?? selectedRunId}</span>
              <em>{translateAssistantText('Waiting for your approval', locale)}</em>
              <div>
                <Button icon={<Icon name="eye" />} variant="ghost" onClick={onViewApprovals}>
                  {text.review}
                </Button>
                <Button icon={<Icon name="check" />} variant="primary" onClick={onViewApprovals}>
                  {text.approve}
                </Button>
              </div>
            </div>
          </RailSection>

          <RailSection title={text.executionPreviewDryRun}>
            <Badge tone="success">{text.safe}</Badge>
            <div className="assistant-diff-preview" aria-label="Dry run diff preview">
              <span>1 | # Dry run: rollout restart</span>
              <span className="diff-remove">2 | - replicas: 3</span>
              <span className="diff-add">3 | + replicas: 3</span>
              <span>4 | ~ pod template hash changed</span>
              <span>5 | ~ restart strategy: RollingUpdate</span>
            </div>
            <Button variant="ghost" onClick={onViewRuns}>
              {text.viewFullDiff}
            </Button>
          </RailSection>

          <RailSection title={text.policyChecks}>
            <div className="assistant-policy-checks">
              {['Change is permitted by active policies', 'Target is in approved namespace', 'Risk level accepted for this operation'].map(
                (item) => (
                  <span key={item}>
                    <StatusDot tone="success" /> {translateAssistantText(item, locale)}
                  </span>
                ),
              )}
            </div>
          </RailSection>

          <RailSection title={text.recentActivity} action={text.viewAll} onAction={onViewRuns}>
            <div className="assistant-rail-list">
              {['Health check failed: operator queue', 'Auto-diagnosis completed', 'Run initiated by user'].map(
                (item, index) => (
                  <button type="button" key={item} onClick={onViewRuns}>
                    <StatusDot tone={index === 0 ? 'error' : index === 1 ? 'info' : 'success'} />
                    <span>
                      <strong>{translateAssistantText(item, locale)}</strong>
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
