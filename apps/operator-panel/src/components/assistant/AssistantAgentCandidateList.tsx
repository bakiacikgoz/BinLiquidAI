import type { AssistantTaskAgentCandidate } from '../../assistant/assistantTaskingTypes';
import { Badge } from '../primitives/Badge';

export function AssistantAgentCandidateList({ agents }: { agents: AssistantTaskAgentCandidate[] }) {
  if (agents.length === 0) {
    return <p className="assistant-empty-state">No enrolled agent candidates matched this request.</p>;
  }

  return (
    <ul className="assistant-task-agent-list">
      {agents.map((agent) => (
        <li key={agent.agentId}>
          <div>
            <strong>{agent.label}</strong>
            <span>{agent.agentId}</span>
          </div>
          <Badge tone={agent.enrolled ? 'success' : 'error'}>{agent.enrolled ? 'enrolled' : 'not enrolled'}</Badge>
          <em>{agent.qualificationStatus}</em>
        </li>
      ))}
    </ul>
  );
}
