import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { artifactBridge } from '../../artifact-workspace/artifactBridge';
import { AgentRegistryView } from '../../components/control-plane/AgentRegistryView';
import { decideApproval, fetchApprovals, listControlPlaneAgents, showApproval } from '../../bridge';
import { loadSettings } from '../../settings';

type ApprovalRow = { approvalId: string; targetKind: string; status: string };

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? value as Record<string, unknown> : {};
}

function pendingApprovals(value: unknown): ApprovalRow[] {
  const pending = record(value).pending;
  if (!Array.isArray(pending)) return [];
  return pending.flatMap((item) => {
    const row = record(item);
    const approvalId = typeof row.approval_id === 'string' ? row.approval_id : '';
    return approvalId ? [{
      approvalId,
      targetKind: typeof row.target_kind === 'string' ? row.target_kind : 'governed action',
      status: typeof row.status === 'string' ? row.status : 'pending',
    }] : [];
  });
}

export function LibraryPage() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState<Array<{ artifactId: string; title: string; kind: string; status: string }>>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [detail, setDetail] = useState<unknown>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    void artifactBridge.list().then((result) => {
      const next = result.items.map((item) => ({
        artifactId: item.artifactId, title: item.title, kind: item.kind, status: item.status,
      }));
      setItems(next);
      setSelectedArtifactId((current) => next.some((item) => item.artifactId === current) ? current : next[0]?.artifactId ?? null);
    }).catch((cause) => setError(cause instanceof Error ? cause.message : 'Artifact library is unavailable.'));
  }, []);
  useEffect(load, [load]);
  useEffect(() => {
    const requestedArtifactId = searchParams.get('artifact');
    if (requestedArtifactId && items.some((item) => item.artifactId === requestedArtifactId)) {
      setSelectedArtifactId(requestedArtifactId);
    }
  }, [items, searchParams]);
  useEffect(() => {
    if (!selectedArtifactId) { setDetail(null); return; }
    void artifactBridge.get({ artifactId: selectedArtifactId }).then(setDetail)
      .catch((cause) => setError(cause instanceof Error ? cause.message : 'Artifact detail is unavailable.'));
  }, [selectedArtifactId]);
  return <section className="ps-collection"><p className="ps-eyebrow">GOVERNED LIBRARY</p><h1>Library</h1><p>Artifacts are loaded from the existing governed Artifact Workspace, never from demo data.</p><button type="button" onClick={load}>Refresh</button>{error && <p role="alert">{error}</p>}<div className="ps-collection-grid"><div className="ps-collection-list">{items.map((item) => <button type="button" key={item.artifactId} className={selectedArtifactId === item.artifactId ? 'selected' : ''} onClick={() => setSelectedArtifactId(item.artifactId)}><strong>{item.title}</strong><span>{item.kind} · {item.status}</span></button>)}{!items.length && !error && <p className="ps-muted">No governed artifacts are available in this workspace.</p>}</div><article className="ps-collection-detail"><h2>{selectedArtifactId ?? 'No artifact selected'}</h2><pre>{detail ? JSON.stringify(detail, null, 2) : 'Select an artifact to inspect its canonical detail.'}</pre></article></div></section>;
}

export function ApprovalsPage() {
  const [searchParams] = useSearchParams();
  const [settings] = useState(() => loadSettings());
  const [rows, setRows] = useState<ApprovalRow[]>([]);
  const [selected, setSelected] = useState<ApprovalRow | null>(null);
  const [detail, setDetail] = useState<unknown>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    void fetchApprovals(settings).then((value) => {
      const next = pendingApprovals(value);
      setRows(next);
      const requestedApprovalId = searchParams.get('approval');
      setSelected((current) => next.find((item) => item.approvalId === requestedApprovalId)
        ?? next.find((item) => item.approvalId === current?.approvalId)
        ?? next[0] ?? null);
    }).catch((cause) => setError(cause instanceof Error ? cause.message : 'Approvals are unavailable.'));
  }, [searchParams, settings]);
  useEffect(load, [load]);
  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    void showApproval(settings, selected.approvalId).then(setDetail).catch((cause) => setError(cause instanceof Error ? cause.message : 'Approval detail is unavailable.'));
  }, [selected, settings]);
  const decide = async (approve: boolean) => {
    if (!selected || !settings.operatorId.trim()) return;
    if (!window.confirm(`${approve ? 'Approve' : 'Reject'} ${selected.approvalId}?`)) return;
    try {
      await decideApproval(settings, selected.approvalId, approve, settings.operatorId, 'product shell decision');
      load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Approval decision failed.'); }
  };
  const canDecide = Boolean(selected && settings.operatorId.trim());
  return <section className="ps-collection"><p className="ps-eyebrow">GOVERNED APPROVALS</p><h1>Approvals</h1><p>Every approval decision uses the existing identity and approval bridge.</p><button type="button" onClick={load}>Refresh</button>{error && <p role="alert">{error}</p>}<div className="ps-collection-grid"><div className="ps-collection-list">{rows.map((row) => <button type="button" key={row.approvalId} className={selected?.approvalId === row.approvalId ? 'selected' : ''} onClick={() => setSelected(row)}><strong>{row.approvalId}</strong><span>{row.targetKind} · {row.status}</span></button>)}{!rows.length && !error && <p className="ps-muted">No pending approvals.</p>}</div><article className="ps-collection-detail"><h2>{selected?.approvalId ?? 'No approval selected'}</h2><pre>{detail ? JSON.stringify(detail, null, 2) : 'Select an approval to inspect its governed detail.'}</pre><div><button type="button" disabled={!canDecide} onClick={() => void decide(true)}>Approve</button><button type="button" disabled={!canDecide} onClick={() => void decide(false)}>Reject</button></div>{!settings.operatorId.trim() && <p className="ps-muted">Set an operator identity in Settings before deciding.</p>}</article></div></section>;
}

export function AgentsPage() {
  const [searchParams] = useSearchParams();
  const [settings] = useState(() => loadSettings());
  const [agents, setAgents] = useState<unknown>({ agents: [] });
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    setError('');
    void listControlPlaneAgents(settings).then(setAgents).catch((cause) => {
      setAgents({ agents: [] });
      setError(cause instanceof Error ? cause.message : 'Agent registry is unavailable.');
    });
  }, [settings]);
  useEffect(load, [load]);
  const requestedAgentId = searchParams.get('agent');
  return <section className="ps-governed-agents"><div className="ps-collection"><p className="ps-eyebrow">GOVERNED AGENTS</p><button type="button" onClick={load}>Refresh registry</button>{error && <p role="alert">{error}</p>}</div><AgentRegistryView agents={agents} selectedAgentId={selectedAgentId ?? requestedAgentId} onSelectAgent={setSelectedAgentId} /></section>;
}
