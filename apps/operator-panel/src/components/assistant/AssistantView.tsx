import type { ReactNode } from 'react';

import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { Button } from '../primitives/Button';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { AssistantComposer } from './AssistantComposer';
import { AssistantTranscript } from './AssistantTranscript';
import { AssistantWelcome } from './AssistantWelcome';

export type AssistantViewCopy = {
  title: string;
  subtitle: string;
  welcomeTitle: string;
  badgeLabel: string;
  newChat: string;
  messageLabel: string;
  sendLabel: string;
  composerPlaceholder: string;
  readOnlyByDefault: string;
  sensitiveDataNotice: string;
  dryRunSafe: string;
  referencedRuns: string;
  systemHealth: string;
  suggestedPromptsLabel: string;
  suggestedPrompts: string[];
  awaitingContextTitle: string;
  awaitingContextBody: string;
  noReferencedRunTitle: string;
  noReferencedRunBody: string;
  approvalLifecycle: string;
  approvalGated: string;
  approvalLifecycleBody: string;
};

export function AssistantView({
  copy,
  state,
  rightRail = null,
  approvalDisabled = true,
  approvalDisabledReason = '',
  debugRawEnabled = false,
  onSend = () => undefined,
  onNewChat = () => undefined,
  onReviewApproval = () => undefined,
  onApprove = () => undefined,
  onReject = () => undefined,
  onExecute = () => undefined,
}: {
  copy: AssistantViewCopy;
  state: AssistantSessionState;
  rightRail?: ReactNode;
  approvalDisabled?: boolean;
  approvalDisabledReason?: string;
  debugRawEnabled?: boolean;
  onSend?: (message: string) => void;
  onNewChat?: () => void;
  onReviewApproval?: (approvalId: string) => void;
  onApprove?: (approvalId: string) => void;
  onReject?: (approvalId: string) => void;
  onExecute?: (approvalId: string) => void;
}) {
  const currentTurnRunning = state.status === 'starting' || state.status === 'streaming';
  const surfaceState =
    state.status === 'awaiting_approval' ? 'approval' : state.turns.length > 0 ? 'transcript' : 'welcome';

  return (
    <section className={`assistant-surface assistant-surface-${surfaceState}`} aria-labelledby="assistant-title">
      <header className="assistant-top-chrome">
        <div className="assistant-context-switcher" aria-label="Assistant workspace context">
          <div className="assistant-top-select assistant-top-select-wide">
            <span>Workspace</span>
            <strong>
              Production Control Plane <Icon name="chevron" />
            </strong>
          </div>
          <div className="assistant-top-select">
            <span>Policy Mode</span>
            <strong className="assistant-warning-value">
              <Icon name="shield" /> Guarded <Icon name="chevron" />
            </strong>
          </div>
          <div className="assistant-top-select">
            <span>Runtime Status</span>
            <strong className="assistant-success-value">Healthy</strong>
          </div>
        </div>
        <div className="assistant-top-actions">
          <label className="assistant-search">
            <Icon name="logs" />
            <input aria-label="Search assistant context" placeholder="Search" />
            <kbd>⌘K</kbd>
          </label>
          <button type="button" aria-label="Open terminal" disabled title="Terminal access is not available in assistant preview">
            <Icon name="terminal" />
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="assistant-notification-button"
            disabled
            title="Assistant notifications are not available in this context"
          >
            <Icon name="bell" />
            <span aria-hidden="true" />
          </button>
        </div>
      </header>

      <div className="assistant-surface-grid">
        <div className="assistant-main-stage">
          {state.turns.length > 0 ? (
            <header className="assistant-session-header">
              <div className="assistant-title-block">
                <div className="assistant-mark" aria-hidden="true">
                  <Icon name="sparkle" />
                </div>
                <div>
                  <h1 id="assistant-title">{copy.title}</h1>
                  <span>Pro</span>
                </div>
              </div>
              <div className="assistant-session-actions">
                <Button icon={<Icon name="edit" />} variant="ghost" onClick={onNewChat}>
                  {copy.newChat}
                </Button>
                <button
                  type="button"
                  aria-label="More assistant actions"
                  disabled
                  title="More assistant actions are not available yet"
                >
                  ···
                </button>
              </div>
            </header>
          ) : (
            <span id="assistant-title" className="sr-only">
              {copy.title}
            </span>
          )}

          {state.turns.length === 0 ? (
            <AssistantWelcome
              title={copy.welcomeTitle}
              subtitle={copy.subtitle}
              badgeLabel={copy.badgeLabel}
              readOnlyByDefault={copy.readOnlyByDefault}
            />
          ) : (
            <AssistantTranscript
              turns={state.turns}
              approvalDisabled={approvalDisabled}
              approvalDisabledReason={approvalDisabledReason}
              emptyRunLabel={copy.noReferencedRunTitle}
              debugRawEnabled={debugRawEnabled}
              onReviewApproval={onReviewApproval}
              onApprove={onApprove}
              onReject={onReject}
              onExecute={onExecute}
            />
          )}

          {state.turns.length === 0 ? (
            <div className="assistant-context-grid" aria-label="Assistant context">
              <Card className="assistant-context-card">
                <span className="assistant-card-label">{copy.systemHealth}</span>
                <strong>{copy.awaitingContextTitle}</strong>
                <p>{copy.awaitingContextBody}</p>
              </Card>
              <Card className="assistant-context-card">
                <span className="assistant-card-label">{copy.referencedRuns}</span>
                <strong>{copy.noReferencedRunTitle}</strong>
                <p>{copy.noReferencedRunBody}</p>
              </Card>
              <Card className="assistant-context-card">
                <span className="assistant-card-label">{copy.approvalLifecycle}</span>
                <strong>{copy.approvalGated}</strong>
                <p>{copy.approvalLifecycleBody}</p>
              </Card>
            </div>
          ) : null}

          <AssistantComposer
            label={copy.messageLabel}
            placeholder={copy.composerPlaceholder}
            sendLabel={copy.sendLabel}
            disabled={currentTurnRunning}
            onSend={onSend}
          />
        </div>

        {rightRail}
      </div>
    </section>
  );
}
