import { asControlPlaneAgentList } from '../../controlPlaneMappers';

export function AgentRegistryView({ agents }: { agents: unknown }) {
  const list = asControlPlaneAgentList(agents);
  return (
    <section className="workspace" data-testid="page-primary-region">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Registry</p>
          <h2>Agents</h2>
          <p className="workspace-lead">Governed agent and workflow specifications.</p>
        </div>
      </div>
      <div className="section-grid two-up">
        <article className="page-card">
          <h3>Registry</h3>
          <div className="run-list">
            {list.agents.map((agent) => (
              <article className="run-list-item" key={agent.agent_id}>
                <strong>{agent.display_name || agent.agent_id}</strong>
                <span>{`${agent.agent_type} / ${agent.runtime_kind}`}</span>
                <small>{`${agent.status} / ${agent.readiness}`}</small>
                <small>{`Policy ${agent.policy_pack_id} / ${agent.risk_profile}`}</small>
                <small>{`Evidence ${agent.last_evidence_status}`}</small>
              </article>
            ))}
            {list.agents.length === 0 ? (
              <article className="run-list-item">
                <strong>No registered agents</strong>
                <span>Register an agent spec with the control-plane CLI.</span>
                <small>binliquid control-plane agent register</small>
              </article>
            ) : null}
          </div>
        </article>
        <article className="page-card">
          <h3>Governed actions</h3>
          <div className="metric-list">
            <div className="metric-row">
              <span>External gateway</span>
              <strong>{list.agents.some((agent) => agent.agent_type.startsWith('external')) ? 'configured' : 'not registered'}</strong>
            </div>
            <div className="metric-row">
              <span>Approval boundary</span>
              <strong>external writes gated</strong>
            </div>
            <div className="metric-row">
              <span>Evidence status</span>
              <strong>signed pack required</strong>
            </div>
          </div>
        </article>
      </div>
    </section>
  );
}
