import { Icon } from '../primitives/Icon';
import { AssistantSafetyStrip } from './AssistantSafetyStrip';

const promptBodies = [
  'Spot trends and anomalies quickly',
  'Create a step-by-step fix strategy',
  'Show recent updates and impact',
  'Explain what happened in the selected run',
];

export function AssistantWelcome({
  title,
  subtitle,
  badgeLabel,
  suggestedPromptsLabel,
  suggestedPrompts,
  readOnlyByDefault,
  sensitiveDataNotice,
  dryRunSafe,
  onSelectPrompt,
}: {
  title: string;
  subtitle: string;
  badgeLabel: string;
  suggestedPromptsLabel: string;
  suggestedPrompts: string[];
  readOnlyByDefault: string;
  sensitiveDataNotice: string;
  dryRunSafe: string;
  onSelectPrompt: (prompt: string) => void;
}) {
  const aegisIndex = title.indexOf('AegisOS');
  const highlightedTitle =
    aegisIndex >= 0 ? (
      <>
        {title.slice(0, aegisIndex)}
        <span>AegisOS</span>
        {title.slice(aegisIndex + 'AegisOS'.length)}
      </>
    ) : (
      title
    );

  return (
    <div className="assistant-welcome-card">
      <div className="assistant-hero-line" aria-hidden="true" />
      <div className="assistant-hero-mark" aria-hidden="true">
        <Icon name="sparkle" />
      </div>
      <div className="assistant-welcome-copy">
        <h2 aria-label={title}>{highlightedTitle}</h2>
        <p>{subtitle}</p>
        <div className="assistant-welcome-chips" aria-label={badgeLabel}>
          <span className="assistant-chip-success">
            <Icon name="shield" /> Policy-aware
          </span>
          <span>
            <Icon name="approval" /> {readOnlyByDefault}
          </span>
          <span className="assistant-chip-warning">
            <Icon name="check" /> Approval protected
          </span>
          <span>
            <Icon name="layers" /> Enterprise secure
          </span>
        </div>
      </div>

      <div className="assistant-prompt-divider">
        <span>{suggestedPromptsLabel}</span>
      </div>
      <div className="assistant-prompt-grid" aria-label={suggestedPromptsLabel}>
        {suggestedPrompts.map((prompt, index) => (
          <button
            className={`assistant-prompt-card assistant-prompt-card-${index + 1}`}
            type="button"
            key={prompt}
            onClick={() => onSelectPrompt(prompt)}
          >
            <span className="assistant-prompt-icon">
              <Icon name={index === 0 ? 'logs' : index === 1 ? 'list' : index === 2 ? 'shield' : 'gauge'} />
            </span>
            <span>
              <strong>{prompt}</strong>
              <small>{promptBodies[index] ?? prompt}</small>
            </span>
            <Icon name="chevron" />
          </button>
        ))}
      </div>

      <AssistantSafetyStrip
        readOnlyByDefault={readOnlyByDefault}
        sensitiveDataNotice={sensitiveDataNotice}
        dryRunSafe={dryRunSafe}
      />
    </div>
  );
}
