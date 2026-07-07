import type { AssistantKnowledgeSourceRef } from '../../assistant/assistantTypes';
import { Badge } from '../primitives/Badge';
import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';

export function AssistantKnowledgeSourcesCard({
  sources,
  compact = false,
}: {
  sources: AssistantKnowledgeSourceRef[];
  compact?: boolean;
}) {
  const Wrapper = compact ? 'div' : Card;
  return (
    <Wrapper className={compact ? 'assistant-knowledge-card compact' : 'assistant-knowledge-card'}>
      <div className="assistant-knowledge-card-head">
        <span>
          <Icon name="logs" /> Knowledge Sources
        </span>
        <Badge tone={sources.length > 0 ? 'success' : 'warning'}>{sources.length > 0 ? 'grounded' : 'unavailable'}</Badge>
      </div>
      {sources.length > 0 ? (
        <ul className="assistant-knowledge-source-list">
          {sources.slice(0, compact ? 4 : 8).map((source) => (
            <li key={`${source.path}:${source.heading}`}>
              <strong>{source.heading || source.path}</strong>
              <span>{source.path}</span>
              <em>{Math.round(source.score * 100)}% match</em>
            </li>
          ))}
        </ul>
      ) : (
        <p className="assistant-empty-state">
          Local system knowledge is not attached. Run the knowledge doctor or rebuild the index.
        </p>
      )}
    </Wrapper>
  );
}
