export type ControlPlaneAgentList = {
  agents: Array<{
    agent_id: string;
    display_name: string;
    runtime_kind: string;
    status: string;
    readiness: string;
    last_run_id: string | null;
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
