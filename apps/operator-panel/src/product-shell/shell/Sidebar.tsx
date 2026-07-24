import { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';

import { useProductShellStore } from '../state/productShellStore';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';

export function Sidebar() {
  const tasks = useProductShellStore((state) => state.tasks);
  const selectedTaskId = useProductShellStore((state) => state.selectedTaskId);
  const selectTask = useProductShellStore((state) => state.selectTask);
  const collapsed = useProductShellStore((state) => state.sidebarCollapsed);
  const setCollapsed = useProductShellStore((state) => state.setSidebarCollapsed);
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query.trim().toLowerCase()), 180);
    return () => window.clearTimeout(timer);
  }, [query]);
  useEffect(() => {
    void productWorkspaceClient.listProjects().then(async ({ projects }) => {
      const groups = await Promise.all(projects.map((project) => productWorkspaceClient.listTasks(project.projectId)));
      upsertTasks(groups.flatMap((group) => group.tasks.map((task) => ({ id: task.taskId, title: task.title, createdAt: task.createdAtUtc, status: task.status === 'completed' ? 'completed' : 'active', assistantSessionId: task.assistantSessionId ?? undefined }))));
    }).catch(() => undefined);
  }, [upsertTasks]);
  const visibleTasks = useMemo(
    () => debouncedQuery ? tasks.filter((task) => task.title.toLowerCase().includes(debouncedQuery)) : tasks,
    [debouncedQuery, tasks],
  );
  return <aside className="ps-sidebar" aria-label="Product navigation">
    <div className="ps-brand-row"><NavLink to="/" className="ps-brand">IMPERAOS <small>PRODUCT</small></NavLink><button type="button" aria-label="Toggle sidebar" onClick={() => setCollapsed(!collapsed)}>☰</button></div>
    <nav><NavLink to="/">New work</NavLink><NavLink to="/library">Library</NavLink><NavLink to="/approvals">Approvals</NavLink><NavLink to="/settings">Settings</NavLink></nav>
    <label className="ps-search"><span>Search tasks</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search…" /></label>
    <div className="ps-sidebar-heading">RECENT TASKS</div>
    <ul>{visibleTasks.length ? visibleTasks.map((task) => <li key={task.id}><NavLink onClick={() => selectTask(task.id)} className={selectedTaskId === task.id ? 'selected' : ''} to={`/task/${task.id}`}>{task.title}<small>{task.status}</small></NavLink></li>) : <li className="ps-muted">{query ? 'No matching tasks.' : 'Tasks appear after you start work.'}</li>}</ul>
  </aside>;
}
