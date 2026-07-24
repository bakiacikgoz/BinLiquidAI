import { useCallback, useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';

import { productWorkspaceClient, type ProductWorkspaceProject } from '../adapters/productWorkspaceClient';
import { useProductShellStore } from '../state/productShellStore';
import { GlobalSearch } from './GlobalSearch';

type ProjectSort = 'updated_desc' | 'manual' | 'priority';

export function Sidebar() {
  const tasks = useProductShellStore((state) => state.tasks);
  const selectedTaskId = useProductShellStore((state) => state.selectedTaskId);
  const selectTask = useProductShellStore((state) => state.selectTask);
  const collapsed = useProductShellStore((state) => state.sidebarCollapsed);
  const setCollapsed = useProductShellStore((state) => state.setSidebarCollapsed);
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const [projects, setProjects] = useState<ProductWorkspaceProject[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [sort, setSort] = useState<ProjectSort>('manual');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const loadProjects = useCallback(async (cursor?: string, append = false) => {
    try {
      setError('');
      const page = await productWorkspaceClient.listProjects({ cursor, limit: 25, status: 'active', sort });
      setProjects((current) => append ? [...current, ...page.projects] : page.projects);
      setNextCursor(page.nextCursor);
      const groups = await Promise.all(page.projects.map((project) => productWorkspaceClient.listTasks(project.projectId)));
      upsertTasks(groups.flatMap((group) => group.tasks.map((task) => ({
        id: task.taskId,
        title: task.title,
        createdAt: task.createdAtUtc,
        status: task.status === 'completed' ? 'completed' : 'active',
        assistantSessionId: task.assistantSessionId ?? undefined,
      }))));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load governed projects.');
    }
  }, [sort, upsertTasks]);

  useEffect(() => { void loadProjects(); }, [loadProjects]);

  const mutate = async (action: () => Promise<unknown>) => {
    try {
      setBusy(true);
      setError('');
      await action();
      await loadProjects();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update governed project.');
    } finally {
      setBusy(false);
    }
  };

  return <aside className="ps-sidebar" aria-label="Product navigation">
    <div className="ps-brand-row"><NavLink to="/" className="ps-brand">IMPERAOS <small>PRODUCT</small></NavLink><button type="button" aria-label="Toggle sidebar" onClick={() => setCollapsed(!collapsed)}>☰</button></div>
    <nav><NavLink to="/">New work</NavLink><NavLink to="/library">Library</NavLink><NavLink to="/approvals">Approvals</NavLink><NavLink to="/settings">Settings</NavLink></nav>
    <GlobalSearch />
    <section className="ps-projects" aria-label="Projects">
      <div className="ps-sidebar-heading ps-project-heading">PROJECTS <button type="button" disabled={busy} onClick={() => void mutate(async () => { await productWorkspaceClient.registerProjectFromFolder(); })}>Add project</button></div>
      <label className="ps-project-sort">Sort projects<select aria-label="Sort projects" value={sort} onChange={(event) => setSort(event.target.value as ProjectSort)}><option value="manual">Manual</option><option value="updated_desc">Recently updated</option><option value="priority">Pinned first</option></select></label>
      {error && <p role="alert">{error}</p>}
      <ul>{projects.length ? projects.map((project) => <li key={project.projectId} className="ps-project-row">
        <NavLink to={`/?project=${encodeURIComponent(project.projectId)}`}>{project.title}<small>{project.rootDisplayName}</small></NavLink>
        <div className="ps-project-actions">
          <button type="button" disabled={busy} aria-label={`${project.pinned ? 'Unpin' : 'Pin'} ${project.title}`} onClick={() => void mutate(() => productWorkspaceClient.updateProject(project.projectId, { pinned: !project.pinned }))}>{project.pinned ? 'Unpin' : 'Pin'}</button>
          <button type="button" disabled={busy || project.manualOrder === 0} aria-label={`Move ${project.title} up`} onClick={() => void mutate(() => productWorkspaceClient.updateProject(project.projectId, { manualOrder: Math.max(0, project.manualOrder - 1) }))}>↑</button>
          <button type="button" disabled={busy} aria-label={`Archive ${project.title}`} onClick={() => void mutate(() => productWorkspaceClient.archiveProject(project.projectId, 'Archived from sidebar'))}>Archive</button>
        </div>
      </li>) : <li className="ps-muted">Choose a folder to register a governed project.</li>}</ul>
      {nextCursor && <button type="button" className="ps-load-more" disabled={busy} onClick={() => void loadProjects(nextCursor, true)}>Load more projects</button>}
    </section>
    <div className="ps-sidebar-heading">RECENT TASKS</div>
    <ul>{tasks.length ? tasks.map((task) => <li key={task.id}><NavLink onClick={() => selectTask(task.id)} className={selectedTaskId === task.id ? 'selected' : ''} to={`/task/${task.id}`}>{task.title}<small>{task.status}</small></NavLink></li>) : <li className="ps-muted">Tasks appear after you start work.</li>}</ul>
  </aside>;
}
