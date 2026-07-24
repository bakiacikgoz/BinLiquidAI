import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Composer } from '../composer/Composer';
import { useProductShellStore } from '../state/productShellStore';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';

export function NewWorkPage() {
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const start = async (message: string) => {
    try {
      setError('');
      const project = await productWorkspaceClient.createProject('Operator work');
      const task = await productWorkspaceClient.createTask(project.projectId, message);
      upsertTasks([{ id: task.taskId, title: task.title, createdAt: task.createdAtUtc, status: task.status === 'completed' ? 'completed' : 'active', assistantSessionId: task.assistantSessionId ?? undefined }]);
      navigate(`/task/${task.taskId}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create governed work.'); }
  };
  return <section className="ps-new-work"><div><p className="ps-eyebrow">GOVERNED OPERATOR WORKSPACE</p><h1>What should ImperaOS help you accomplish?</h1><p>Plan a task, inspect the evidence, and route changes through the existing approval and artifact controls.</p>{error && <p role="alert">{error}</p>}</div><Composer onSend={(message) => void start(message)} /></section>;
}
