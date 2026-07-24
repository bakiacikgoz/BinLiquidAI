import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useAssistantModels } from '../../assistant/useAssistantModels';
import type { AssistantProviderKind } from '../../assistant/modelDiscovery';
import type { AssistantComposerControls } from '../../assistant/assistantTypes';
import { AssistantComposer } from '../../components/assistant/AssistantComposer';
import {
  getAssistantRuntimeSettings,
  loadSettings,
  resolveLocale,
  saveSettings,
  type AssistantRuntimeSettings,
  type PanelSettings,
} from '../../settings';
import { useProductShellStore } from '../state/productShellStore';
import { productWorkspaceClient, type ProductWorkspaceProject } from '../adapters/productWorkspaceClient';

export function NewWorkPage() {
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const upsertProjects = useProductShellStore((state) => state.upsertProjects);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<ProductWorkspaceProject[]>([]);
  const [projectId, setProjectId] = useState('');
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const modelProvider = settings.assistantProvider.trim()
    ? settings.assistantProvider.trim() as AssistantProviderKind
    : 'all';
  const modelDiscovery = useAssistantModels({
    settings,
    profile: settings.profile,
    provider: modelProvider,
  });
  useEffect(() => {
    let active = true;
    void productWorkspaceClient.listProjects().then(({ projects }) => {
      if (!active) return;
      const activeProjects = projects.filter((project) => project.status !== 'archived');
      setProjects(activeProjects);
      upsertProjects(activeProjects.map((project) => ({
        projectId: project.projectId,
        rootRef: project.rootRef,
        rootDisplayName: project.rootDisplayName,
      })));
      const requestedProjectId = searchParams.get('project');
      if (requestedProjectId && activeProjects.some((project) => project.projectId === requestedProjectId)) {
        setProjectId(requestedProjectId);
      }
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : 'Could not load governed projects.');
    });
    return () => { active = false; };
  }, [searchParams, upsertProjects]);
  const updateRuntimeSettings = (next: Partial<AssistantRuntimeSettings>) => {
    setSettings((current) => {
      const updated = { ...current, ...next };
      saveSettings(updated);
      return updated;
    });
  };
  const start = async (
    message: string,
    runtimeSettings: AssistantRuntimeSettings,
    controls: AssistantComposerControls,
  ) => {
    try {
      setError('');
      const selectedProjectId = projectId || (await productWorkspaceClient.getOrCreateProject('Operator work')).projectId;
      const assistantSessionId = `product-session-${crypto.randomUUID()}`;
      const task = await productWorkspaceClient.createTask(selectedProjectId, message, assistantSessionId, {
        reasoningEffort: runtimeSettings.reasoningEffort ?? 'medium',
        speedProfile: runtimeSettings.speedProfile ?? 'standard',
        approvalProfile: runtimeSettings.approvalProfile ?? 'risk_based',
      });
      await productWorkspaceClient.addMessage(task.taskId, 'user', message);
      upsertTasks([{ id: task.taskId, projectId: task.projectId, title: task.title, createdAt: task.createdAtUtc, updatedAt: task.updatedAtUtc, status: task.status, priority: task.priority, pinned: task.pinned, manualOrder: task.manualOrder, archivedAt: task.archivedAtUtc, assistantSessionId: task.assistantSessionId ?? undefined, reasoningEffort: task.reasoningEffort, speedProfile: task.speedProfile, approvalProfile: task.approvalProfile }]);
      navigate(`/task/${task.taskId}`, { state: { initialMessage: message, runtimeSettings, controls } });
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create governed work.'); }
  };
  return <section className="ps-new-work"><div><p className="ps-eyebrow">GOVERNED OPERATOR WORKSPACE</p><h1>What should ImperaOS help you accomplish?</h1><p>Plan a task, inspect the evidence, and route changes through the existing approval and artifact controls.</p><label>Project<select aria-label="Project" value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Default governed project (create if needed)</option>{projects.map((project) => <option key={project.projectId} value={project.projectId}>{project.title}</option>)}</select></label>{error && <p role="alert">{error}</p>}</div><AssistantComposer label="Governed assistant" placeholder="Describe the outcome you need…" sendLabel="Start work" disabled={false} runtimeSettings={getAssistantRuntimeSettings(settings)} modelDiscovery={modelDiscovery} locale={resolveLocale(settings.locale)} onRuntimeSettingsChange={updateRuntimeSettings} onSend={(message, runtimeSettings, controls) => void start(message, runtimeSettings, controls)} /></section>;
}
