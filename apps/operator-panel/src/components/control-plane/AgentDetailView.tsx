import { RawInspector } from './RawInspector';

export function AgentDetailView({ agent }: { agent: unknown }) {
  return <RawInspector value={agent} label="Agent raw payload" />;
}
