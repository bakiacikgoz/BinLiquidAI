import {
  Copy,
  ExternalLink,
  FileText,
  RefreshCw,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { MarkdownAnswer } from '../../components/assistant/AssistantMessage';
import { TurnActivity } from './TurnActivity';
import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { productWorkspaceClient, type ProductTaskLink } from '../adapters/productWorkspaceClient';
import { transientConversationTurns, type StoredMessage } from './conversationState';

type ProductConversationViewProps = {
  state: AssistantSessionState;
  taskId: string;
  refreshToken?: number;
  onOpenArtifacts?: (artifactId?: string) => void;
  onOpenApproval?: (approvalId: string) => void;
  onRegenerate?: (turnId: string) => void;
};

function copyMessage(body: string) {
  void globalThis.navigator?.clipboard?.writeText(body);
}

function MessageFeedback({
  body,
  onRegenerate,
}: {
  body: string;
  onRegenerate?: () => void;
}) {
  return (
    <div className="message-feedback">
      <button type="button" title="Copy" onClick={() => copyMessage(body)}><Copy size={15} /></button>
      {onRegenerate ? <button type="button" title="Regenerate" onClick={onRegenerate}><RefreshCw size={15} /></button> : null}
    </div>
  );
}

export function ProductConversationView({
  state,
  taskId,
  refreshToken = 0,
  onOpenArtifacts,
  onOpenApproval,
  onRegenerate,
}: ProductConversationViewProps) {
  const scrollPane = useRef<HTMLElement>(null);
  const followLatest = useRef(true);
  const [showLatest, setShowLatest] = useState(false);
  const [stored, setStored] = useState<StoredMessage[]>([]);
  const [links, setLinks] = useState<ProductTaskLink[]>([]);
  const [loadError, setLoadError] = useState('');
  const [retryToken, setRetryToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoadError('');
    void Promise.all([productWorkspaceClient.listMessages(taskId), productWorkspaceClient.listLinks(taskId)])
      .then(([{ messages }, { links: nextLinks }]) => {
        if (!active) return;
        setStored(messages);
        setLinks(nextLinks);
      })
      .catch((cause) => {
        if (!active) return;
        setLoadError(cause instanceof Error ? cause.message : 'Could not load the durable conversation.');
      });
    return () => { active = false; };
  }, [refreshToken, retryToken, taskId]);

  useEffect(() => {
    if (followLatest.current && scrollPane.current) scrollPane.current.scrollTop = scrollPane.current.scrollHeight;
  }, [state.turns, stored]);

  const transient = transientConversationTurns(state, stored);
  const empty = !loadError && !state.turns.length && !stored.length;

  return (
    <section ref={scrollPane} className="conversation-view" aria-label="Assistant conversation" onScroll={() => { const el = scrollPane.current; if (!el) return; followLatest.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80; setShowLatest(!followLatest.current); }}>
      {showLatest && <button type="button" className="conversation-jump" onClick={() => { followLatest.current = true; if (scrollPane.current) scrollPane.current.scrollTop = scrollPane.current.scrollHeight; setShowLatest(false); }}>Son mesaja git ↓</button>}
      <div className="conversation-inner">
        {loadError ? (
          <section className="conversation-empty" role="alert">
            <h2>Conversation unavailable</h2>
            <p>{loadError}</p>
            <button type="button" onClick={() => setRetryToken((current) => current + 1)}>Retry durable conversation</button>
          </section>
        ) : null}
        {empty ? (
          <section className="conversation-empty ps-empty">
            <h2>Start governed work</h2>
            <p>ImperaOS will plan, enforce policy, and keep a trace of the run.</p>
          </section>
        ) : null}

        {stored.map((message) => (
          message.role === 'user' ? (
            <article className="user-message" key={message.messageId}>
              <p>{message.body}</p>
            </article>
          ) : (
            <div className="assistant-message-block" key={message.messageId}>
              {(() => { const completed = state.turns.find((turn) => turn.status === 'completed' && turn.assistantMessage.text.trim() === message.body); return completed ? <TurnActivity turn={completed} /> : null; })()}
              <article className="completion-message">
                <MarkdownAnswer text={message.body} />
              </article>
              <MessageFeedback body={message.body} />
            </div>
          )
        ))}

        {transient.map((turn) => {
          const sourceTurn = state.turns.find((candidate) => candidate.id === turn.id);
          const approval = sourceTurn?.assistantMessage.approval;
          const isWorking = sourceTurn?.status === 'streaming' || sourceTurn?.status === 'starting';
          return (
            <div className="assistant-turn" key={turn.id}>
              {turn.user ? <article className="user-message"><p>{turn.user}</p></article> : null}
              {sourceTurn && <TurnActivity turn={sourceTurn} />}
              {turn.assistant ? <article className={isWorking ? 'completion-message is-streaming' : 'completion-message'}><MarkdownAnswer text={turn.assistant} /></article> : null}
              {(approval || (!isWorking && turn.assistant)) ? (
                <>
                  <div className="conversation-actions">
                    {approval && onOpenApproval ? (
                      <div className="conversation-approval-card"><span><strong>{approval.title || 'Onay gerekiyor'}</strong><small>Devam etmek için işlemi inceleyin.</small></span><button type="button" aria-label="Open approval" onClick={() => onOpenApproval(approval.approvalId)}>İncele</button></div>
                    ) : null}
                  </div>
                  <MessageFeedback
                    body={turn.assistant ?? turn.user ?? ''}
                    onRegenerate={turn.assistant && onRegenerate ? () => onRegenerate(turn.id) : undefined}
                  />
                </>
              ) : null}
            </div>
          );
        })}

        {state.referencedArtifacts.filter((artifact) => artifact.openable && artifact.artifactId).length ? (
          <section className="reference-documents" aria-label="Referenced artifacts">
            {[...new Map(state.referencedArtifacts.filter((artifact) => artifact.openable && artifact.artifactId).map((artifact) => [artifact.artifactId, artifact])).values()]
              .map((artifact) => (
                <button
                  type="button"
                  className="reference-document-card"
                  aria-label="Open in workspace"
                  key={`${artifact.artifactId}:${artifact.revisionId ?? ''}`}
                  onClick={() => onOpenArtifacts?.(artifact.artifactId)}
                >
                  <span className="reference-document-icon"><FileText size={22} /></span>
                  <span>
                    <strong>{artifact.name}</strong>
                    <small>{artifact.kind ?? 'artifact'} · {artifact.summary ?? 'Governed artifact available'}</small>
                  </span>
                  <span className="reference-document-open">İncele <ExternalLink size={15} /></span>
                </button>
              ))}
          </section>
        ) : null}

        {links.length ? (
          <section className="change-summary-card durable-task-links" aria-label="Durable task links">
            <header>
              <span className="change-summary-icon"><FileText size={19} /></span>
              <span><strong>Çalışma kaynakları</strong><small>{links.length} governed reference{links.length === 1 ? '' : 's'}</small></span>
            </header>
            {links.map((link) => (
              <div className="changed-file-row" key={link.linkId}>
                <code>{link.targetType}</code>
                <span>{link.targetId}</span>
                {link.targetType === 'artifact' ? (
                  <button type="button" onClick={() => onOpenArtifacts?.(link.targetId)}>
                    Open artifact {link.targetId}
                  </button>
                ) : null}
                {link.targetType === 'approval' ? (
                  <button type="button" onClick={() => onOpenApproval?.(link.targetId)}>
                    Open approval {link.targetId}
                  </button>
                ) : null}
                {link.targetType === 'run' ? <span className="ps-muted">Governed run reference</span> : null}
                {link.targetType === 'team_job' ? <span className="ps-muted">Governed team job reference</span> : null}
              </div>
            ))}
          </section>
        ) : null}
      </div>
    </section>
  );
}
