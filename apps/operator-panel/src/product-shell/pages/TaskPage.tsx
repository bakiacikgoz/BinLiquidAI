import { useEffect, useRef, useState } from 'react';
import { Navigate, useParams } from 'react-router-dom';

import { BottomDock } from '../bottom-dock/BottomDock';
import { Composer } from '../composer/Composer';
import { ContextRail } from '../context-rail/ContextRail';
import { ProductConversationView } from '../conversation/ProductConversationView';
import { useProductAssistant } from '../adapters/useProductAssistant';
import { useProductShellStore } from '../state/productShellStore';
import { WorkSurface } from '../workspace/WorkSurface';
import { ProductArtifactWorkspace } from '../workspace/ProductArtifactWorkspace';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';

export function TaskPage() {
  const { taskId } = useParams();
  const task = useProductShellStore((state) => state.tasks.find((item) => item.id === taskId));
  const selectTask = useProductShellStore((state) => state.selectTask);
  const contextRailOpen = useProductShellStore((state) => state.contextRailOpen);
  const setContextRailOpen = useProductShellStore((state) => state.setContextRailOpen);
  const assistant = useProductAssistant(task);
  const [artifactOpenRequest, setArtifactOpenRequest] = useState(0);
  const [messageRefreshToken, setMessageRefreshToken] = useState(0);
  const persistedAssistantTurns = useRef(new Set<string>());
  useEffect(() => { if (taskId) selectTask(taskId); }, [selectTask, taskId]);
  useEffect(() => {
    if (!task) return;
    assistant.state.turns.forEach((turn) => {
      const body = turn.assistantMessage.text.trim();
      const persistenceKey = `${task.id}:${turn.id}:${body}`;
      if (turn.status !== 'completed' || !body || persistedAssistantTurns.current.has(persistenceKey)) return;
      persistedAssistantTurns.current.add(persistenceKey);
      void productWorkspaceClient.addMessage(task.id, 'assistant', body)
        .then(() => setMessageRefreshToken((current) => current + 1))
        .catch(() => persistedAssistantTurns.current.delete(persistenceKey));
    });
  }, [assistant.state.turns, task]);
  if (!task) return <Navigate to="/" replace />;
  const running = assistant.state.status === 'starting' || assistant.state.status === 'streaming';
  const send = async (message: string) => {
    await productWorkspaceClient.addMessage(task.id, 'user', message);
    setMessageRefreshToken((current) => current + 1);
    await assistant.actions.send(message);
  };
  return <section className="ps-task"><header className="ps-topbar"><div><p className="ps-eyebrow">ACTIVE TASK</p><h1>{task.title}</h1></div><button type="button" onClick={() => setContextRailOpen(!contextRailOpen)}>Context</button></header>
    <div className="ps-task-grid"><div className="ps-task-center"><ProductConversationView state={assistant.state} taskId={task.id} refreshToken={messageRefreshToken} /><Composer disabled={running} onSend={(message) => void send(message)} /><WorkSurface taskTitle={task.title} onOpenArtifacts={() => setArtifactOpenRequest((current) => current + 1)} /><ProductArtifactWorkspace key={task.id} state={assistant.state} openRequest={artifactOpenRequest} /><BottomDock state={assistant.state} /></div>{contextRailOpen && <ContextRail task={task} />}</div>
  </section>;
}
