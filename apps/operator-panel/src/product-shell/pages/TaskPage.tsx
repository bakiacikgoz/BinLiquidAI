import { useEffect } from 'react';
import { Navigate, useParams } from 'react-router-dom';

import { BottomDock } from '../bottom-dock/BottomDock';
import { Composer } from '../composer/Composer';
import { ContextRail } from '../context-rail/ContextRail';
import { ProductConversationView } from '../conversation/ProductConversationView';
import { useProductAssistant } from '../adapters/useProductAssistant';
import { useProductShellStore } from '../state/productShellStore';
import { WorkSurface } from '../workspace/WorkSurface';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';

export function TaskPage() {
  const { taskId } = useParams();
  const task = useProductShellStore((state) => state.tasks.find((item) => item.id === taskId));
  const selectTask = useProductShellStore((state) => state.selectTask);
  const contextRailOpen = useProductShellStore((state) => state.contextRailOpen);
  const setContextRailOpen = useProductShellStore((state) => state.setContextRailOpen);
  const assistant = useProductAssistant(task);
  useEffect(() => { if (taskId) selectTask(taskId); }, [selectTask, taskId]);
  if (!task) return <Navigate to="/" replace />;
  const running = assistant.state.status === 'starting' || assistant.state.status === 'streaming';
  const send = async (message: string) => {
    await productWorkspaceClient.addMessage(task.id, 'user', message);
    await assistant.actions.send(message);
  };
  return <section className="ps-task"><header className="ps-topbar"><div><p className="ps-eyebrow">ACTIVE TASK</p><h1>{task.title}</h1></div><button type="button" onClick={() => setContextRailOpen(!contextRailOpen)}>Context</button></header>
    <div className="ps-task-grid"><div className="ps-task-center"><ProductConversationView state={assistant.state} /><Composer disabled={running} onSend={(message) => void send(message)} /><WorkSurface taskTitle={task.title} /><BottomDock state={assistant.state} /></div>{contextRailOpen && <ContextRail task={task} />}</div>
  </section>;
}
