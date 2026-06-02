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
        agent_type: readAgentType(agent, 'agent_type'),
        status: readString(agent, 'status'),
        readiness: readString(agent, 'readiness'),
        owner_team: readNullableString(agent, 'owner_team'),
        policy_pack_id: readString(agent, 'policy_pack_id') || 'active-runtime-policy',
        risk_profile: readRiskProfile(agent, 'risk_profile'),
        last_run_id: readNullableString(agent, 'last_run_id'),
        last_evidence_pack_id: readNullableString(agent, 'last_evidence_pack_id'),
        last_evidence_status: readEvidenceStatus(agent, 'last_evidence_status'),
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

function readAgentType(source: Record<string, unknown>, key: string): ControlPlaneAgentList['agents'][number]['agent_type'] {
  const value = readString(source, key);
  if (value === 'external_stdio' || value === 'external_http' || value === 'computer_use_adapter') {
    return value;
  }
  return 'internal';
}

function readRiskProfile(source: Record<string, unknown>, key: string): ControlPlaneAgentList['agents'][number]['risk_profile'] {
  const value = readString(source, key);
  if (value === 'read_only' || value === 'restricted' || value === 'blocked') {
    return value;
  }
  return 'guarded';
}

function readEvidenceStatus(
  source: Record<string, unknown>,
  key: string,
): ControlPlaneAgentList['agents'][number]['last_evidence_status'] {
  const value = readString(source, key);
  if (value === 'pending' || value === 'valid' || value === 'invalid') {
    return value;
  }
  return 'missing';
}
