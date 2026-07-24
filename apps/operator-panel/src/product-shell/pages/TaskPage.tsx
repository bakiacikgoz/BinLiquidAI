import { useEffect, useRef, useState } from 'react';
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';

import { useAssistantModels } from '../../assistant/useAssistantModels';
import type { AssistantProviderKind } from '../../assistant/modelDiscovery';
import type { AssistantComposerControls } from '../../assistant/assistantTypes';
import { BottomDock } from '../bottom-dock/BottomDock';
import { ContextRail } from '../context-rail/ContextRail';
import { ProductConversationView } from '../conversation/ProductConversationView';
import { useProductAssistant } from '../adapters/useProductAssistant';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';
import { useProductShellStore, type ProductTask } from '../state/productShellStore';
import { WorkSurface } from '../workspace/WorkSurface';
import { ProductArtifactWorkspace } from '../workspace/ProductArtifactWorkspace';
import { AssistantComposer } from '../../components/assistant/AssistantComposer';
import {
  getAssistantRuntimeSettings,
  loadSettings,
  resolveLocale,
  saveSettings,
  type AssistantRuntimeSettings,
  type PanelSettings,
} from '../../settings';

type InitialTaskNavigationState = { initialMessage?: unknown } | null;

export function TaskPage() {
  const { taskId } = useParams();
  const task = useProductShellStore((state) => state.tasks.find((item) => item.id === taskId));
  const selectTask = useProductShellStore((state) => state.selectTask);
  useEffect(() => { if (taskId) selectTask(taskId); }, [selectTask, taskId]);
  if (!task) return <Navigate to="/" replace />;
  return <TaskWorkspace key={task.id} task={task} />;
}

function TaskWorkspace({ task }: { task: ProductTask }) {
  const location = useLocation();
  const navigate = useNavigate();
  const contextRailOpen = useProductShellStore((state) => state.contextRailOpen);
  const setContextRailOpen = useProductShellStore((state) => state.setContextRailOpen);
  const assistant = useProductAssistant(task);
  const [artifactOpenRequest, setArtifactOpenRequest] = useState(0);
  const [messageRefreshToken, setMessageRefreshToken] = useState(0);
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const persistedAssistantTurns = useRef(new Set<string>());
  const initialTurnStarted = useRef(false);
  const modelProvider = settings.assistantProvider.trim()
    ? settings.assistantProvider.trim() as AssistantProviderKind
    : 'all';
  const modelDiscovery = useAssistantModels({
    settings,
    profile: settings.profile,
    provider: modelProvider,
  });

  useEffect(() => {
    const state = location.state as InitialTaskNavigationState;
    const initialMessage = typeof state?.initialMessage === 'string' ? state.initialMessage.trim() : '';
    if (!initialMessage || initialTurnStarted.current) return;
    initialTurnStarted.current = true;
    navigate(location.pathname, { replace: true, state: null });
    void assistant.actions.send(initialMessage);
  }, [assistant.actions, location.pathname, location.state, navigate]);

  useEffect(() => {
    assistant.state.turns.forEach((turn) => {
      const body = turn.assistantMessage.text.trim();
      const persistenceKey = `${task.id}:${turn.id}:${body}`;
      if (turn.status !== 'completed' || !body || persistedAssistantTurns.current.has(persistenceKey)) return;
      persistedAssistantTurns.current.add(persistenceKey);
      void productWorkspaceClient.addMessage(task.id, 'assistant', body)
        .then(() => setMessageRefreshToken((current) => current + 1))
        .catch(() => persistedAssistantTurns.current.delete(persistenceKey));
    });
  }, [assistant.state.turns, task.id]);

  const running = assistant.state.status === 'starting' || assistant.state.status === 'streaming';
  const updateRuntimeSettings = (next: Partial<AssistantRuntimeSettings>) => {
    setSettings((current) => {
      const updated = { ...current, ...next };
      saveSettings(updated);
      return updated;
    });
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
  return <section className="ps-task"><header className="ps-topbar"><div><p className="ps-eyebrow">ACTIVE TASK</p><h1>{task.title}</h1></div><button type="button" onClick={() => setContextRailOpen(!contextRailOpen)}>Context</button></header>
    <div className="ps-task-grid"><div className="ps-task-center"><ProductConversationView state={assistant.state} taskId={task.id} refreshToken={messageRefreshToken} /><AssistantComposer label="Governed assistant" placeholder="Describe the next outcome…" sendLabel="Send" disabled={running} statusLabel={assistant.state.status} runtimeSettings={getAssistantRuntimeSettings(settings)} modelDiscovery={modelDiscovery} locale={resolveLocale(settings.locale)} onRuntimeSettingsChange={updateRuntimeSettings} onSend={(message, runtimeSettings, controls) => void send(message, runtimeSettings, controls)} onCancel={() => void assistant.actions.cancel()} /><WorkSurface taskTitle={task.title} onOpenArtifacts={() => setArtifactOpenRequest((current) => current + 1)} /><ProductArtifactWorkspace state={assistant.state} openRequest={artifactOpenRequest} /><BottomDock state={assistant.state} /></div>{contextRailOpen && <ContextRail task={task} />}</div>
  </section>;
}
