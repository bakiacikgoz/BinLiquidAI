export function AgentDetailView({ agent }: { agent: unknown }) {
  return <pre className="json-panel">{JSON.stringify(agent ?? {}, null, 2)}</pre>;
}
