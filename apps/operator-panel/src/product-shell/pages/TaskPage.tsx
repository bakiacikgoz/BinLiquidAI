import { useCallback, useEffect, useRef, useState } from 'react';
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';

import { useAssistantModels } from '../../assistant/useAssistantModels';
import type { AssistantProviderKind } from '../../assistant/modelDiscovery';
import type { AssistantComposerControls } from '../../assistant/assistantTypes';
import { BottomDock } from '../bottom-dock/BottomDock';
import { ContextRail } from '../context-rail/ContextRail';
import { ProductConversationView } from '../conversation/ProductConversationView';
import { useProductAssistant } from '../adapters/useProductAssistant';
import { productWorkspaceClient, type ProductWorkspaceTask } from '../adapters/productWorkspaceClient';
import { useProductShellStore, type ProductTask } from '../state/productShellStore';
import { WorkSurface } from '../workspace/WorkSurface';
import { WorkspaceTabs } from '../workspace/WorkspaceTabs';
import { createWorkspaceTab, type WorkspaceTab, type WorkspaceTabKind } from '../workspace/workspaceTabState';
import { AssistantComposer } from '../../components/assistant/AssistantComposer';
import {
  getAssistantRuntimeSettings,
  loadSettings,
  resolveLocale,
  saveSettings,
  type AssistantRuntimeSettings,
  type PanelSettings,
} from '../../settings';

type InitialTaskNavigationState = {
  initialMessage?: unknown;
  runtimeSettings?: unknown;
  controls?: unknown;
} | null;

function runtimeSettingsFromNavigation(value: unknown): AssistantRuntimeSettings | undefined {
  if (typeof value !== 'object' || value === null) return undefined;
  const source = value as Record<string, unknown>;
  const keys: Array<keyof AssistantRuntimeSettings> = [
    'assistantProvider', 'assistantFallbackProvider', 'assistantModel', 'assistantHfModelId',
  ];
  if (!keys.every((key) => typeof source[key] === 'string')) return undefined;
  return {
    assistantProvider: source.assistantProvider as string,
    assistantFallbackProvider: source.assistantFallbackProvider as string,
    assistantModel: source.assistantModel as string,
    assistantHfModelId: source.assistantHfModelId as string,
    reasoningEffort: ['low', 'medium', 'high', 'very_high'].includes(String(source.reasoningEffort))
      ? source.reasoningEffort as AssistantRuntimeSettings['reasoningEffort'] : 'medium',
    speedProfile: ['standard', 'fast'].includes(String(source.speedProfile))
      ? source.speedProfile as AssistantRuntimeSettings['speedProfile'] : 'standard',
    approvalProfile: ['always_ask', 'risk_based', 'policy_automatic'].includes(String(source.approvalProfile))
      ? source.approvalProfile as AssistantRuntimeSettings['approvalProfile'] : 'risk_based',
  };
}

function shellTask(task: ProductWorkspaceTask): ProductTask {
  return {
    id: task.taskId,
    projectId: task.projectId,
    title: task.title,
    createdAt: task.createdAtUtc,
    updatedAt: task.updatedAtUtc,
    status: task.status,
    priority: task.priority,
    pinned: task.pinned,
    manualOrder: task.manualOrder,
    archivedAt: task.archivedAtUtc,
    assistantSessionId: task.assistantSessionId ?? undefined,
    reasoningEffort: task.reasoningEffort,
    speedProfile: task.speedProfile,
    approvalProfile: task.approvalProfile,
  };
}

function controlsFromNavigation(value: unknown): AssistantComposerControls | undefined {
  if (typeof value !== 'object' || value === null) return undefined;
  const source = value as Record<string, unknown>;
  const attachmentKinds = ['active_run', 'event_tail', 'approval_summary', 'artifact_summary', 'system_health'] as const;
  const toolIntents = ['inspect_run', 'summarize_events', 'explain_policy_blocker', 'draft_remediation_plan', 'prepare_approval_review'] as const;
  if (!Array.isArray(source.contextAttachmentKinds) || !Array.isArray(source.toolIntents)
    || !source.contextAttachmentKinds.every((item) => attachmentKinds.includes(item as typeof attachmentKinds[number]))
    || !source.toolIntents.every((item) => toolIntents.includes(item as typeof toolIntents[number]))) return undefined;
  return {
    contextAttachmentKinds: source.contextAttachmentKinds as AssistantComposerControls['contextAttachmentKinds'],
    toolIntents: source.toolIntents as AssistantComposerControls['toolIntents'],
  };
}

export function TaskPage() {
  const { taskId } = useParams();
  const task = useProductShellStore((state) => state.tasks.find((item) => item.id === taskId));
  const selectTask = useProductShellStore((state) => state.selectTask);
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const [loadError, setLoadError] = useState('');
  useEffect(() => { if (taskId) selectTask(taskId); }, [selectTask, taskId]);
  useEffect(() => {
    if (!taskId || task) return;
    let active = true;
    setLoadError('');
    void productWorkspaceClient.getTask(taskId).then((loaded) => {
      if (!active) return;
      upsertTasks([shellTask(loaded)]);
    }).catch((cause) => {
      if (active) setLoadError(cause instanceof Error ? cause.message : 'Task is unavailable.');
    });
    return () => { active = false; };
  }, [task, taskId, upsertTasks]);
  if (!taskId) return <Navigate to="/" replace />;
  if (!task) return <section className="ps-empty" aria-live="polite"><h2>{loadError ? 'Task unavailable' : 'Loading governed task…'}</h2><p>{loadError || 'Restoring the durable task and its governed runtime context.'}</p>{loadError && <a href="#/">Return to new work</a>}</section>;
  return <TaskWorkspace key={task.id} task={task} />;
}

function TaskWorkspace({ task }: { task: ProductTask }) {
  const location = useLocation();
  const navigate = useNavigate();
  const contextRailOpen = useProductShellStore((state) => state.contextRailOpen);
  const setContextRailOpen = useProductShellStore((state) => state.setContextRailOpen);
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const projects = useProductShellStore((state) => state.projects);
  const assistant = useProductAssistant(task);
  const [workspaceTabs, setWorkspaceTabs] = useState<WorkspaceTab[]>([]);
  const [activeWorkspaceTabId, setActiveWorkspaceTabId] = useState<string | null>(null);
  const [messageRefreshToken, setMessageRefreshToken] = useState(0);
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const persistedAssistantTurns = useRef(new Set<string>());
  const persistedTaskLinks = useRef(new Set<string>());
  const initialTurnStarted = useRef(false);
  const modelProvider = settings.assistantProvider.trim()
    ? settings.assistantProvider.trim() as AssistantProviderKind
    : 'all';
  const modelDiscovery = useAssistantModels({
    settings,
    profile: settings.profile,
    provider: modelProvider,
  });
  const taskRuntimeSettings: AssistantRuntimeSettings = {
    ...getAssistantRuntimeSettings(settings),
    reasoningEffort: task.reasoningEffort ?? 'medium',
    speedProfile: task.speedProfile ?? 'standard',
    approvalProfile: task.approvalProfile ?? 'risk_based',
  };
  const projectRoot = task.projectId
    ? projects.find((project) => project.projectId === task.projectId)
    : undefined;

  useEffect(() => {
    const state = location.state as InitialTaskNavigationState;
    const initialMessage = typeof state?.initialMessage === 'string' ? state.initialMessage.trim() : '';
    if (!initialMessage || initialTurnStarted.current) return;
    initialTurnStarted.current = true;
    navigate(location.pathname, { replace: true, state: null });
    void assistant.actions.send(
      initialMessage,
      runtimeSettingsFromNavigation(state?.runtimeSettings) ?? taskRuntimeSettings,
      controlsFromNavigation(state?.controls),
    );
  }, [assistant.actions, location.pathname, location.state, navigate, taskRuntimeSettings]);

  useEffect(() => {
    assistant.state.turns.forEach((turn) => {
      const body = turn.assistantMessage.text.trim();
      const persistenceKey = `${task.id}:${turn.id}:${body}`;
      if (turn.status !== 'completed') return;
      if (body && !persistedAssistantTurns.current.has(persistenceKey)) {
        persistedAssistantTurns.current.add(persistenceKey);
        void productWorkspaceClient.addMessage(task.id, 'assistant', body)
          .then(() => setMessageRefreshToken((current) => current + 1))
          .catch(() => persistedAssistantTurns.current.delete(persistenceKey));
      }
      const durableLinks: Array<{ targetType: 'artifact' | 'approval' | 'team_job' | 'run'; targetId: string }> = [
        ...turn.assistantMessage.referencedArtifacts
          .flatMap((artifact) => artifact.artifactId ? [{ targetType: 'artifact' as const, targetId: artifact.artifactId }] : []),
        ...turn.assistantMessage.referencedRuns
          .map((run) => ({ targetType: 'run' as const, targetId: run.id })),
        ...(turn.assistantMessage.approval ? [{ targetType: 'approval' as const, targetId: turn.assistantMessage.approval.approvalId }] : []),
      ];
      durableLinks.forEach((link) => {
        const linkKey = `${task.id}:${link.targetType}:${link.targetId}`;
        if (persistedTaskLinks.current.has(linkKey)) return;
        persistedTaskLinks.current.add(linkKey);
        void productWorkspaceClient.addLink(task.id, link.targetType, link.targetId)
          .then(() => setMessageRefreshToken((current) => current + 1))
          .catch(() => persistedTaskLinks.current.delete(linkKey));
      });
    });
  }, [assistant.state.turns, task.id]);

  const running = assistant.state.status === 'starting' || assistant.state.status === 'streaming';
  const updateRuntimeSettings = (next: Partial<AssistantRuntimeSettings>) => {
    setSettings((current) => {
      const updated = { ...current, ...next };
      saveSettings(updated);
      return updated;
    });
    const runtime = {
      reasoningEffort: next.reasoningEffort ?? taskRuntimeSettings.reasoningEffort ?? 'medium',
      speedProfile: next.speedProfile ?? taskRuntimeSettings.speedProfile ?? 'standard',
      approvalProfile: next.approvalProfile ?? taskRuntimeSettings.approvalProfile ?? 'risk_based',
    };
    if (next.reasoningEffort || next.speedProfile || next.approvalProfile) {
      void productWorkspaceClient.updateTask(task.id, { runtime })
        .then((updated) => upsertTasks([shellTask(updated)]))
        .catch(() => undefined);
    }
  };
  const send = async (
    message: string,
    runtimeSettings?: AssistantRuntimeSettings,
    controls?: AssistantComposerControls,
  ) => {
    await productWorkspaceClient.addMessage(task.id, 'user', message);
    setMessageRefreshToken((current) => current + 1);
    await assistant.actions.send(message, runtimeSettings, controls);
  };
  const openWorkspaceTab = useCallback((kind: WorkspaceTabKind, artifactId?: string) => {
    setWorkspaceTabs((current) => {
      const existing = kind === 'artifacts' ? current.find((tab) => tab.kind === 'artifacts') : undefined;
      const next = existing
        ? { ...existing, ...(artifactId ? { artifactId } : {}) }
        : createWorkspaceTab(kind, artifactId);
      setActiveWorkspaceTabId(next.id);
      return existing ? current.map((tab) => tab.id === existing.id ? next : tab) : [...current, next];
    });
  }, []);
  const closeWorkspaceTab = (tabId: string) => {
    setWorkspaceTabs((current) => {
      const next = current.filter((tab) => tab.id !== tabId);
      setActiveWorkspaceTabId((active) => active === tabId ? (next.at(-1)?.id ?? null) : active);
      return next;
    });
  };
  const updateWorkspaceTab = (tabId: string, changes: Partial<WorkspaceTab>) => {
    setWorkspaceTabs((current) => current.map((tab) => tab.id === tabId ? { ...tab, ...changes } : tab));
  };
  useEffect(() => {
    if (location.pathname.endsWith('/workspace')) openWorkspaceTab('artifacts');
  }, [location.pathname, openWorkspaceTab]);
  const readOnly = task.status === 'archived';
  return <section className="ps-task"><header className="ps-topbar"><div><p className="ps-eyebrow">{task.status.toUpperCase()} TASK</p><h1>{task.title}</h1></div><div><button type="button" onClick={() => navigate(`/task/${task.id}/workspace`)}>Open workspace</button><button type="button" onClick={() => setContextRailOpen(!contextRailOpen)}>Context</button></div></header>
    <div className="ps-task-grid"><div className="ps-task-center">{readOnly && <p className="ps-archive-banner" role="status">This task is archived and read-only.</p>}<ProductConversationView state={assistant.state} taskId={task.id} refreshToken={messageRefreshToken} onOpenArtifacts={(artifactId) => openWorkspaceTab('artifacts', artifactId)} onOpenApproval={(approvalId) => navigate(`/approvals?approval=${encodeURIComponent(approvalId)}`)} onRegenerate={(turnId) => void assistant.actions.regenerate(turnId, taskRuntimeSettings)} /><AssistantComposer label="Governed assistant" placeholder="Describe the next outcome…" sendLabel="Send" disabled={running || readOnly} statusLabel={assistant.state.status} runtimeSettings={taskRuntimeSettings} modelDiscovery={modelDiscovery} locale={resolveLocale(settings.locale)} onRuntimeSettingsChange={updateRuntimeSettings} onSend={(message, runtimeSettings, controls) => void send(message, runtimeSettings, controls)} onCancel={() => void (async () => { await assistant.actions.cancel(); const updated = await productWorkspaceClient.updateTask(task.id, { status: 'cancelled' }); upsertTasks([shellTask(updated)]); })()} /><WorkSurface taskTitle={task.title} onOpenArtifacts={() => openWorkspaceTab('artifacts')} onOpenTerminal={() => openWorkspaceTab('terminal')} onOpenBrowser={() => openWorkspaceTab('browser')} onOpenPreview={() => openWorkspaceTab('preview')} /><WorkspaceTabs tabs={workspaceTabs} activeTabId={activeWorkspaceTabId} assistantState={assistant.state} projectRootRef={projectRoot?.rootRef} projectRootDisplayName={projectRoot?.rootDisplayName} onActivate={setActiveWorkspaceTabId} onClose={closeWorkspaceTab} onUpdate={updateWorkspaceTab} /><BottomDock state={assistant.state} /></div>{contextRailOpen && <ContextRail task={task} state={assistant.state} />}</div>
  </section>;
}
