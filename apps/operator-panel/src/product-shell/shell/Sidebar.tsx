import { useEffect } from 'react';
import { NavLink } from 'react-router-dom';

import { useProductShellStore } from '../state/productShellStore';
import { productWorkspaceClient } from '../adapters/productWorkspaceClient';
import { GlobalSearch } from './GlobalSearch';

export function Sidebar() {
  const tasks = useProductShellStore((state) => state.tasks);
  const selectedTaskId = useProductShellStore((state) => state.selectedTaskId);
  const selectTask = useProductShellStore((state) => state.selectTask);
  const collapsed = useProductShellStore((state) => state.sidebarCollapsed);
  const setCollapsed = useProductShellStore((state) => state.setSidebarCollapsed);
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  useEffect(() => {
    void productWorkspaceClient.listProjects().then(async ({ projects }) => {
      const groups = await Promise.all(projects.map((project) => productWorkspaceClient.listTasks(project.projectId)));
      upsertTasks(groups.flatMap((group) => group.tasks.map((task) => ({ id: task.taskId, title: task.title, createdAt: task.createdAtUtc, status: task.status === 'completed' ? 'completed' : 'active', assistantSessionId: task.assistantSessionId ?? undefined }))));
    }).catch(() => undefined);
  }, [upsertTasks]);
  return <aside className="ps-sidebar" aria-label="Product navigation">
    <div className="ps-brand-row"><NavLink to="/" className="ps-brand">IMPERAOS <small>PRODUCT</small></NavLink><button type="button" aria-label="Toggle sidebar" onClick={() => setCollapsed(!collapsed)}>☰</button></div>
    <nav><NavLink to="/">New work</NavLink><NavLink to="/library">Library</NavLink><NavLink to="/approvals">Approvals</NavLink><NavLink to="/settings">Settings</NavLink></nav>
    <GlobalSearch />
    <div className="ps-sidebar-heading">RECENT TASKS</div>
    <ul>{tasks.length ? tasks.map((task) => <li key={task.id}><NavLink onClick={() => selectTask(task.id)} className={selectedTaskId === task.id ? 'selected' : ''} to={`/task/${task.id}`}>{task.title}<small>{task.status}</small></NavLink></li>) : <li className="ps-muted">Tasks appear after you start work.</li>}</ul>
  </aside>;
}
