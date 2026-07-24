import { NavLink } from 'react-router-dom';

import { useProductShellStore } from '../state/productShellStore';

export function Sidebar() {
  const tasks = useProductShellStore((state) => state.tasks);
  const selectedTaskId = useProductShellStore((state) => state.selectedTaskId);
  const selectTask = useProductShellStore((state) => state.selectTask);
  const collapsed = useProductShellStore((state) => state.sidebarCollapsed);
  const setCollapsed = useProductShellStore((state) => state.setSidebarCollapsed);
  return <aside className="ps-sidebar" aria-label="Product navigation">
    <div className="ps-brand-row"><NavLink to="/" className="ps-brand">IMPERAOS <small>PRODUCT</small></NavLink><button type="button" aria-label="Toggle sidebar" onClick={() => setCollapsed(!collapsed)}>☰</button></div>
    <nav><NavLink to="/">New work</NavLink><NavLink to="/library">Library</NavLink><NavLink to="/approvals">Approvals</NavLink><NavLink to="/settings">Settings</NavLink></nav>
    <div className="ps-sidebar-heading">RECENT TASKS</div>
    <ul>{tasks.length ? tasks.map((task) => <li key={task.id}><NavLink onClick={() => selectTask(task.id)} className={selectedTaskId === task.id ? 'selected' : ''} to={`/task/${task.id}`}>{task.title}<small>{task.status}</small></NavLink></li>) : <li className="ps-muted">Tasks appear after you start work.</li>}</ul>
  </aside>;
}
