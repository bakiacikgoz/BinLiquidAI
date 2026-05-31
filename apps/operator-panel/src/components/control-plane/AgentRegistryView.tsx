import { asControlPlaneAgentList } from '../../controlPlaneMappers';

export function AgentRegistryView({ agents }: { agents: unknown }) {
  const list = asControlPlaneAgentList(agents);
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Registry</p>
          <h2>Agents</h2>
          <p className="workspace-lead">Governed agent and workflow specifications.</p>
        </div>
      </div>
      <div className="run-list">
        {list.agents.map((agent) => (
          <article className="run-list-item" key={agent.agent_id}>
            <strong>{agent.display_name || agent.agent_id}</strong>
            <span>{agent.runtime_kind}</span>
            <small>{`${agent.status} / ${agent.readiness}`}</small>
          </article>
        ))}
        {list.agents.length === 0 ? <p className="empty-state">No registered agents.</p> : null}
      </div>
    </section>
  );
}
