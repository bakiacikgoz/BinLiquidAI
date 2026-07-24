import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { artifactBridge } from '../../artifact-workspace/artifactBridge';
import { asControlPlaneAgentList } from '../../controlPlaneMappers';
import { fetchApprovals, listControlPlaneAgents } from '../../bridge';
import { loadSettings } from '../../settings';
import {
  productWorkspaceClient,
  type ProductWorkspaceProject,
  type ProductWorkspaceTask,
} from '../adapters/productWorkspaceClient';

type SearchKind = 'project' | 'task' | 'artifact' | 'approval' | 'agent' | 'route' | 'command';
type SearchResult = { id: string; kind: SearchKind; title: string; detail: string; path: string };

type SearchData = {
  projects: ProductWorkspaceProject[];
  tasks: ProductWorkspaceTask[];
  artifacts: Array<{ artifactId: string; title: string; kind: string; status: string }>;
  approvals: Array<{ approvalId: string; targetKind: string; status: string }>;
  agents: Array<{ agentId: string; title: string; detail: string }>;
};

const EMPTY_DATA: SearchData = { projects: [], tasks: [], artifacts: [], approvals: [], agents: [] };
const ROUTES: SearchResult[] = [
  { id: 'route:new', kind: 'route', title: 'New work', detail: 'Create governed work', path: '/' },
  { id: 'route:library', kind: 'route', title: 'Library', detail: 'Governed artifacts', path: '/library' },
  { id: 'route:approvals', kind: 'route', title: 'Approvals', detail: 'Pending governed decisions', path: '/approvals' },
  { id: 'route:agents', kind: 'route', title: 'Agents', detail: 'Governed agent registry', path: '/agents' },
  { id: 'route:settings', kind: 'route', title: 'Settings', detail: 'Product and runtime settings', path: '/settings' },
  { id: 'command:new', kind: 'command', title: 'Command: create new work', detail: 'Open the governed work composer', path: '/' },
];

function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? value as Record<string, unknown> : {};
}

function approvalsFrom(value: unknown): SearchData['approvals'] {
  const pending = record(value).pending;
  if (!Array.isArray(pending)) return [];
  return pending.flatMap((item) => {
    const approval = record(item);
    const approvalId = typeof approval.approval_id === 'string' ? approval.approval_id : '';
    return approvalId ? [{
      approvalId,
      targetKind: typeof approval.target_kind === 'string' ? approval.target_kind : 'governed action',
      status: typeof approval.status === 'string' ? approval.status : 'pending',
    }] : [];
  });
}

async function loadSearchData(): Promise<SearchData> {
  const settings = loadSettings();
  const [workspace, artifacts, approvals, agents] = await Promise.allSettled([
    productWorkspaceClient.listProjects().then(async ({ projects }) => ({
      projects,
      tasks: (await Promise.all(projects.map((project) => productWorkspaceClient.listTasks(project.projectId))))
        .flatMap((result) => result.tasks),
    })),
    artifactBridge.list(),
    fetchApprovals(settings),
    listControlPlaneAgents(settings),
  ]);
  const agentRows = agents.status === 'fulfilled' ? asControlPlaneAgentList(agents.value).agents : [];
  return {
    projects: workspace.status === 'fulfilled' ? workspace.value.projects : [],
    tasks: workspace.status === 'fulfilled' ? workspace.value.tasks : [],
    artifacts: artifacts.status === 'fulfilled'
      ? artifacts.value.items.map((item) => ({ artifactId: item.artifactId, title: item.title, kind: item.kind, status: item.status }))
      : [],
    approvals: approvals.status === 'fulfilled' ? approvalsFrom(approvals.value) : [],
    agents: agentRows.map((agent) => ({
      agentId: agent.agent_id,
      title: agent.display_name || agent.agent_id,
      detail: `${agent.agent_type} · ${agent.status}`,
    })),
  };
}

function matchingResults(data: SearchData, query: string): SearchResult[] {
  const projects = data.projects.map((project) => ({
    id: `project:${project.projectId}`, kind: 'project' as const, title: project.title,
    detail: project.status, path: `/?project=${encodeURIComponent(project.projectId)}`,
  }));
  const projectTitles = new Map(data.projects.map((project) => [project.projectId, project.title]));
  const tasks = data.tasks.map((task) => ({
    id: `task:${task.taskId}`, kind: 'task' as const, title: task.title,
    detail: projectTitles.get(task.projectId) ?? task.status, path: `/task/${encodeURIComponent(task.taskId)}`,
  }));
  const artifacts = data.artifacts.map((artifact) => ({
    id: `artifact:${artifact.artifactId}`, kind: 'artifact' as const, title: artifact.title,
    detail: `${artifact.kind} · ${artifact.status}`, path: `/library?artifact=${encodeURIComponent(artifact.artifactId)}`,
  }));
  const approvals = data.approvals.map((approval) => ({
    id: `approval:${approval.approvalId}`, kind: 'approval' as const, title: approval.approvalId,
    detail: `${approval.targetKind} · ${approval.status}`, path: `/approvals?approval=${encodeURIComponent(approval.approvalId)}`,
  }));
  const agents = data.agents.map((agent) => ({
    id: `agent:${agent.agentId}`, kind: 'agent' as const, title: agent.title,
    detail: agent.detail, path: `/agents?agent=${encodeURIComponent(agent.agentId)}`,
  }));
  const candidates = [...tasks, ...projects, ...artifacts, ...approvals, ...agents, ...ROUTES];
  if (!query) return tasks.slice(0, 10);
  return candidates.filter((item) => `${item.title} ${item.detail} ${item.kind}`.toLowerCase().includes(query)).slice(0, 25);
}

export function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [data, setData] = useState<SearchData>(EMPTY_DATA);
  const [status, setStatus] = useState('');

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim().toLowerCase()), 180);
    return () => window.clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    let active = true;
    setStatus('Loading governed search…');
    void loadSearchData().then((next) => {
      if (!active) return;
      setData(next);
      setStatus('');
    }).catch(() => {
      if (active) setStatus('Search sources are unavailable.');
    });
    return () => { active = false; };
  }, []);

  const results = useMemo(() => matchingResults(data, debouncedQuery), [data, debouncedQuery]);
  return <section className="ps-global-search" aria-label="Global search"><label><span>Search</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search work, artifacts, approvals…" /></label>{status ? <p className="ps-muted" role="status">{status}</p> : null}<ul>{results.map((result) => <li key={result.id}><button type="button" onClick={() => navigate(result.path)}><strong>{result.title}</strong><span>{result.kind} · {result.detail}</span></button></li>)}{!status && !results.length ? <li className="ps-muted">No governed results.</li> : null}</ul></section>;
}
