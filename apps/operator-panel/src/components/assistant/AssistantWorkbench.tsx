import type { AssistantSessionState } from '../../assistant/assistantTypes';
import { translateAssistantText, type UiLocale } from '../../i18n';
import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';

export type AssistantWorkbenchArtifact = {
  name: string;
  summary?: string;
  value?: unknown;
};

function stringifyPreview(value: unknown): string {
  if (value === undefined || value === null) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function previewLines(value: unknown): string[] {
  const text = stringifyPreview(value).trim();
  if (!text) {
    return [];
  }
  return text.split('\n').slice(0, 28);
}

export function AssistantWorkbench({
  state,
  artifacts,
  selectedArtifactName,
  locale = 'en',
  onSelectArtifact,
  onViewRuns,
}: {
  state: AssistantSessionState;
  artifacts: AssistantWorkbenchArtifact[];
  selectedArtifactName: string;
  locale?: UiLocale;
  onSelectArtifact: (name: string) => void;
  onViewRuns: () => void;
}) {
  const activeTurn = state.turns.find((turn) => turn.id === state.activeTurnId) ?? state.turns.at(-1);
  const message = activeTurn?.assistantMessage;
  const selectedArtifact = artifacts.find((artifact) => artifact.name === selectedArtifactName) ?? artifacts[0];
  const lines = previewLines(selectedArtifact?.value);
  const title = locale === 'tr' ? 'Çalışma alanı' : 'Workbench';
  const artifactTitle = locale === 'tr' ? 'Artifact önizleme' : 'Artifact preview';
  const actionTitle = locale === 'tr' ? 'Aktif çıktı' : 'Active output';

  return (
    <aside className="assistant-workbench" aria-label={title}>
      <div className="assistant-workbench-head">
        <span>{title}</span>
        <Badge tone={state.status === 'failed' ? 'error' : state.status === 'awaiting_approval' ? 'warning' : 'info'}>
          {translateAssistantText(state.status, locale)}
        </Badge>
      </div>

      <section className="assistant-workbench-panel">
        <div className="assistant-workbench-panel-head">
          <Icon name="sparkle" />
          <span>{actionTitle}</span>
        </div>
        {message?.proposedAction ? (
          <dl className="assistant-workbench-dl">
            <div>
              <dt>{locale === 'tr' ? 'Aksiyon' : 'Action'}</dt>
              <dd>{translateAssistantText(message.proposedAction.title, locale)}</dd>
            </div>
            <div>
              <dt>{locale === 'tr' ? 'Hedef' : 'Target'}</dt>
              <dd>{message.proposedAction.target}</dd>
            </div>
            <div>
              <dt>{locale === 'tr' ? 'Risk' : 'Risk'}</dt>
              <dd>{message.proposedAction.risk}</dd>
            </div>
          </dl>
        ) : message?.text ? (
          <p className="assistant-workbench-text">{translateAssistantText(message.text, locale)}</p>
        ) : (
          <p className="assistant-empty-state">
            {locale === 'tr' ? 'Asistan çıktısı burada sabitlenir.' : 'Assistant output will stay pinned here.'}
          </p>
        )}
      </section>

      <section className="assistant-workbench-panel">
        <div className="assistant-workbench-panel-head">
          <Icon name="terminal" />
          <span>{artifactTitle}</span>
        </div>
        {artifacts.length > 0 ? (
          <>
            <div className="assistant-workbench-artifacts" role="tablist" aria-label={artifactTitle}>
              {artifacts.map((artifact) => (
                <button
                  type="button"
                  key={artifact.name}
                  className={artifact.name === selectedArtifact?.name ? 'assistant-workbench-artifact-active' : ''}
                  onClick={() => onSelectArtifact(artifact.name)}
                >
                  {artifact.name}
                </button>
              ))}
            </div>
            {selectedArtifact?.summary ? <p className="assistant-workbench-text">{selectedArtifact.summary}</p> : null}
            {lines.length > 0 ? (
              <pre className="assistant-workbench-preview">
                <code>{lines.join('\n')}</code>
              </pre>
            ) : (
              <p className="assistant-empty-state">{locale === 'tr' ? 'Önizleme yok.' : 'No preview available.'}</p>
            )}
            <Button variant="ghost" icon={<Icon name="logs" />} onClick={onViewRuns}>
              {locale === 'tr' ? 'Artifactları aç' : 'Open artifacts'}
            </Button>
          </>
        ) : (
          <p className="assistant-empty-state">
            {locale === 'tr' ? 'Seçili run için artifact yok.' : 'No artifacts for the selected run.'}
          </p>
        )}
      </section>
    </aside>
  );
}
