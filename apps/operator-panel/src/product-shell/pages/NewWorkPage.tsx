import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Composer } from '../composer/Composer';
import { useProductShellStore } from '../state/productShellStore';
import { productWorkspaceClient, type ProductWorkspaceProject } from '../adapters/productWorkspaceClient';

export function NewWorkPage() {
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [projects, setProjects] = useState<ProductWorkspaceProject[]>([]);
  const [projectId, setProjectId] = useState('');
  useEffect(() => {
    let active = true;
    void productWorkspaceClient.listProjects().then(({ projects }) => {
      if (!active) return;
      setProjects(projects.filter((project) => project.status !== 'archived'));
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : 'Could not load governed projects.');
    });
    return () => { active = false; };
  }, []);
  const start = async (message: string) => {
    try {
      setError('');
      const selectedProjectId = projectId || (await productWorkspaceClient.getOrCreateProject('Operator work')).projectId;
      const assistantSessionId = `product-session-${crypto.randomUUID()}`;
      const task = await productWorkspaceClient.createTask(selectedProjectId, message, assistantSessionId);
      upsertTasks([{ id: task.taskId, title: task.title, createdAt: task.createdAtUtc, status: task.status === 'completed' ? 'completed' : 'active', assistantSessionId: task.assistantSessionId ?? undefined }]);
      navigate(`/task/${task.taskId}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not create governed work.'); }
  };
  return <section className="ps-new-work"><div><p className="ps-eyebrow">GOVERNED OPERATOR WORKSPACE</p><h1>What should ImperaOS help you accomplish?</h1><p>Plan a task, inspect the evidence, and route changes through the existing approval and artifact controls.</p><label>Project<select aria-label="Project" value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Default governed project (create if needed)</option>{projects.map((project) => <option key={project.projectId} value={project.projectId}>{project.title}</option>)}</select></label>{error && <p role="alert">{error}</p>}</div><Composer onSend={(message) => void start(message)} /></section>;
}
