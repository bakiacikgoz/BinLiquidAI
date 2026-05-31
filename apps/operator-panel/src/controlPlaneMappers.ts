import type { ControlPlaneAgentList, ControlPlaneClaimMatrix } from './controlPlaneTypes';

export function asControlPlaneAgentList(value: unknown): ControlPlaneAgentList {
  const record = asRecord(value);
  const agents = Array.isArray(record.agents) ? record.agents : [];
  return {
    agents: agents.map((item) => {
      const agent = asRecord(item);
      return {
        agent_id: readString(agent, 'agent_id'),
        display_name: readString(agent, 'display_name'),
        runtime_kind: readString(agent, 'runtime_kind'),
        status: readString(agent, 'status'),
        readiness: readString(agent, 'readiness'),
        last_run_id: readNullableString(agent, 'last_run_id'),
      };
    }),
  };
}

export function asControlPlaneClaimMatrix(value: unknown): ControlPlaneClaimMatrix {
  const record = asRecord(value);
  const claims = Array.isArray(record.claims) ? record.claims : [];
  return {
    claims: claims.map((item) => {
      const claim = asRecord(item);
      return {
        claim_id: readString(claim, 'claim_id'),
        status: readString(claim, 'status'),
        required_evidence: readStringList(claim.required_evidence),
        blocking_reasons: readStringList(claim.blocking_reasons),
      };
    }),
  };
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string): string {
  const value = source[key];
  return typeof value === 'string' ? value : '';
}

function readNullableString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' ? value : null;
}

function readStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}
