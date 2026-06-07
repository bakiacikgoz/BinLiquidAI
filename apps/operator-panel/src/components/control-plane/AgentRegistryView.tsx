import { asControlPlaneAgentList } from '../../controlPlaneMappers';
import { CodeToken, StatusBadge } from '../primitives/Token';

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
                <div className="run-list-main">
                  <strong>{agent.display_name || agent.agent_id}</strong>
                  <div className="run-list-meta">
                    <CodeToken>{agent.agent_type}</CodeToken>
                    <CodeToken>{agent.runtime_kind}</CodeToken>
                    <span>{`Policy ${agent.policy_pack_id}`}</span>
                    <span>{agent.risk_profile}</span>
                    <span>{`Evidence ${agent.last_evidence_status}`}</span>
                  </div>
                </div>
                <StatusBadge tone={agent.status === 'active' ? 'success' : 'warning'}>
                  {`${agent.status} / ${agent.readiness}`}
                </StatusBadge>
              </article>
            ))}
            {list.agents.length === 0 ? (
              <article className="run-list-item">
                <div className="run-list-main">
                  <strong>No registered agents</strong>
                  <span>Register an agent spec with the control-plane CLI.</span>
                </div>
                <CodeToken>binliquid control-plane agent register</CodeToken>
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
