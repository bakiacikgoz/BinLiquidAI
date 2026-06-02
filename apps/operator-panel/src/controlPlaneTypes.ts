export type ControlPlaneAgentList = {
  agents: Array<{
    agent_id: string;
    display_name: string;
    runtime_kind: string;
    agent_type: 'internal' | 'external_stdio' | 'external_http' | 'computer_use_adapter';
    status: string;
    readiness: string;
    owner_team: string | null;
    policy_pack_id: string;
    risk_profile: 'read_only' | 'guarded' | 'restricted' | 'blocked';
    last_run_id: string | null;
    last_evidence_pack_id: string | null;
    last_evidence_status: 'missing' | 'pending' | 'valid' | 'invalid';
  }>;
};

export type ControlPlaneClaimMatrix = {
  claims: Array<{
    claim_id: string;
    status: string;
    required_evidence: string[];
    blocking_reasons: string[];
  }>;
};
