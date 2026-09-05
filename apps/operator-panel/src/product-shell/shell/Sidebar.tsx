import {
  Archive,
  ArrowUp,
  Blocks,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CirclePlus,
  Clock3,
  Folder,
  GitPullRequest,
  MoreHorizontal,
  Orbit,
  PanelLeftClose,
  PanelLeftOpen,
  Pin,
  Plus,
  Search,
  RotateCcw,
  Settings,
  SquarePen,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';

import { productWorkspaceClient, type ProductWorkspaceProject } from '../adapters/productWorkspaceClient';
import { SidebarTaskMenu } from './SidebarTaskMenu';
import { SidebarInfoRow } from './SidebarInfoRow';
import { useProductShellStore } from '../state/productShellStore';

type ProjectSort = 'updated_desc' | 'manual' | 'priority';

const primaryLinks = [
  { label: 'Yeni görev', icon: SquarePen, to: '/', trailingIcon: CirclePlus },
  { label: 'Onaylar', icon: GitPullRequest, to: '/approvals' },
  { label: 'Çalışma kütüphanesi', icon: Blocks, to: '/library' },
  { label: 'Zamanlananlar', icon: Clock3, to: '/automations' },
  { label: 'Ajanlar', icon: Orbit, to: '/agents' },
];

function shellTask(task: Awaited<ReturnType<typeof productWorkspaceClient.getTask>>) {
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

function SidebarRowActions({
  title,
  pinned,
  busy,
  canMoveUp,
  onPin,
  onMoveUp,
  onArchive,
}: {
  title: string;
  pinned: boolean;
  busy: boolean;
  canMoveUp: boolean;
  onPin: () => void;
  onMoveUp: () => void;
  onArchive: () => void;
}) {
  return (
    <span className="sidebar-row-actions">
      <button
        className={`sidebar-row-action ${pinned ? 'is-pinned' : ''}`}
        type="button"
        disabled={busy}
        aria-label={`${pinned ? 'Unpin' : 'Pin'} ${title}`}
        title={pinned ? 'Sabitlemeyi kaldır' : 'Sabitle'}
        onClick={onPin}
      >
        <Pin size={12} />
      </button>
      <button
        className="sidebar-row-action"
        type="button"
        disabled={busy || !canMoveUp}
        aria-label={`Move ${title} up`}
        title="Yukarı taşı"
        onClick={onMoveUp}
      >
        <ArrowUp size={12} />
      </button>
      <button
        className="sidebar-row-action"
        type="button"
        disabled={busy}
        aria-label={`Archive ${title}`}
        title="Arşivle"
        onClick={onArchive}
      >
        <Archive size={12} />
      </button>
    </span>
  );
}

export function Sidebar() {
  const navigate = useNavigate();
  const tasks = useProductShellStore((state) => state.tasks);
  const selectedTaskId = useProductShellStore((state) => state.selectedTaskId);
  const selectTask = useProductShellStore((state) => state.selectTask);
  const collapsed = useProductShellStore((state) => state.sidebarCollapsed);
  const setCollapsed = useProductShellStore((state) => state.setSidebarCollapsed);
  const setSearchOpen = useProductShellStore((state) => state.setSearchOpen);
  const upsertTasks = useProductShellStore((state) => state.upsertTasks);
  const upsertProjects = useProductShellStore((state) => state.upsertProjects);
  const sidebarWidth = useProductShellStore((state) => state.sidebarWidth);
  const setSidebarWidth = useProductShellStore((state) => state.setSidebarWidth);
  const [projects, setProjects] = useState<ProductWorkspaceProject[]>([]);
  const [sort, setSort] = useState<ProjectSort>('manual');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [organizeOpen, setOrganizeOpen] = useState(false);
  const [resizing, setResizing] = useState(false);
  const [taskControlsOpen, setTaskControlsOpen] = useState(false);
  const [recentExpanded, setRecentExpanded] = useState(true);
  const [grouping, setGrouping] = useState('project');
  const taskMenuAnchor = useRef<HTMLButtonElement>(null);
  const [sections, setSections] = useState<Array<{ id: string; title: string; taskIds: string[] }>>(() => {
    try {
      const value: unknown = JSON.parse(localStorage.getItem('imperaos-sidebar-sections') || '[]');
      return Array.isArray(value) ? value.filter((item) => item && typeof item.id === 'string' && typeof item.title === 'string' && Array.isArray(item.taskIds) && item.taskIds.every((id: unknown) => typeof id === 'string')) : [];
    } catch { return []; }
  });
  useEffect(() => { localStorage.setItem('imperaos-sidebar-sections', JSON.stringify(sections)); }, [sections]);
  const [taskQuery, setTaskQuery] = useState('');
  const [taskFilter, setTaskFilter] = useState('all');
  const [taskSort, setTaskSort] = useState('recent');
  const [taskError, setTaskError] = useState('');
  const [loading, setLoading] = useState(false);
  const loadGeneration = useRef(0);

  const loadProjects = useCallback(async () => {
    const generation = ++loadGeneration.current;
    setLoading(true);
    setError('');
    setTaskError('');
    try {
      const allProjects: ProductWorkspaceProject[] = [];
      const cursors = new Set<string>();
      let cursor: string | undefined;
      do {
        const page = await productWorkspaceClient.listProjects({ cursor, limit: 25, status: 'active', sort });
        if (generation !== loadGeneration.current) return;
        allProjects.push(...page.projects);
        cursor = page.nextCursor ?? undefined;
        if (cursor && cursors.has(cursor)) throw new Error('Proje listesi tamamlanamadı. Yeniden deneyin.');
        if (cursor) cursors.add(cursor);
      } while (cursor);
      setProjects(allProjects);
      setExpanded((current) => ({ ...Object.fromEntries(allProjects.map((project) => [project.projectId, true])), ...current }));
      upsertProjects(allProjects.map((project) => ({ projectId: project.projectId, rootRef: project.rootRef, rootDisplayName: project.rootDisplayName })));
      const groups = await Promise.allSettled(allProjects.map((project) => productWorkspaceClient.listTasks(project.projectId)));
      if (generation !== loadGeneration.current) return;
      upsertTasks(groups.flatMap((group) => group.status === 'fulfilled' ? group.value.tasks.map(shellTask) : []));
      if (groups.some((group) => group.status === 'rejected')) setTaskError('Bazı projelerin görevleri yüklenemedi. Mevcut görevleri kullanabilir veya yeniden deneyebilirsiniz.');
    } catch (cause) {
      if (generation === loadGeneration.current) setError(cause instanceof Error ? cause.message : 'Projeler yüklenemedi.');
    } finally {
      if (generation === loadGeneration.current) setLoading(false);
    }
  }, [sort, upsertProjects, upsertTasks]);

  useEffect(() => { void loadProjects(); return () => { loadGeneration.current += 1; }; }, [loadProjects]);

  useEffect(() => { const reload = () => { void loadProjects(); }; window.addEventListener('imperaos-projects-changed', reload); return () => window.removeEventListener('imperaos-projects-changed', reload); }, [loadProjects]);

  const mutate = async (action: () => Promise<unknown>) => {
    try {
      setBusy(true);
      setError('');
      await action();
      await loadProjects();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not update governed workspace records.');
    } finally {
      setBusy(false);
    }
  };

  const archiveTask = (taskId: string) => mutate(async () => {
    const changed = await productWorkspaceClient.archiveTask(taskId, 'Archived from sidebar');
    const archivedSelectedTask = useProductShellStore.getState().selectedTaskId === taskId;
    upsertTasks([shellTask(changed)]);
    if (archivedSelectedTask) navigate('/', { replace: true });
  });

  const resizeSidebar = (event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = sidebarWidth;
    setResizing(true);
    const move = (moveEvent: PointerEvent) => setSidebarWidth(startWidth + moveEvent.clientX - startX);
    const end = () => {
      setResizing(false);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', end);
      window.removeEventListener('pointercancel', end);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', end);
    window.addEventListener('pointercancel', end);
  };

  const activeTasks = tasks.filter((task) => task.status !== 'archived');
  const visibleTasks = activeTasks.filter((task) => {
    const matchesStatus = taskFilter === 'all' || (taskFilter === 'open' ? ['draft', 'active', 'awaiting_approval'].includes(task.status) : task.status === taskFilter);
    return !sections.some((section) => section.taskIds.includes(task.id)) && matchesStatus && task.title.toLocaleLowerCase('tr').includes(taskQuery.trim().toLocaleLowerCase('tr'));
  }).sort((a, b) => taskSort === 'manual' ? Number(b.pinned) - Number(a.pinned) || (a.manualOrder ?? 0) - (b.manualOrder ?? 0)
    : taskSort === 'priority' ? (b.priority ?? 0) - (a.priority ?? 0) || Number(b.pinned) - Number(a.pinned)
    : taskSort === 'pinned' ? Number(b.pinned) - Number(a.pinned) || (b.updatedAt ?? b.createdAt).localeCompare(a.updatedAt ?? a.createdAt)
    : (b.updatedAt ?? b.createdAt).localeCompare(a.updatedAt ?? a.createdAt));
  const startConversation = (projectId?: string) => {
    selectTask(null);
    navigate(projectId ? `/?project=${encodeURIComponent(projectId)}` : '/');
  };
  return (
    <aside
      className={`sidebar codex-sidebar ${collapsed ? 'is-collapsed' : ''} ${resizing ? 'is-resizing' : ''}`}
      style={{ width: collapsed ? undefined : sidebarWidth }}
      aria-label="Product navigation"
    >
      <div className="sidebar-utility">
        <button
          className="sidebar-toggle"
          type="button"
          aria-label={collapsed ? 'Kenar çubuğunu aç' : 'Kenar çubuğunu kapat'}
          title={collapsed ? 'Kenar çubuğunu aç' : 'Kenar çubuğunu kapat'}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <PanelLeftOpen size={14} /> : <PanelLeftClose size={14} />}
        </button>
        {!collapsed && (
          <>
            <button className="sidebar-history" type="button" onClick={() => navigate(-1)} title="Geri"><ChevronLeft size={16} /></button>
            <button className="sidebar-history is-muted" type="button" onClick={() => navigate(1)} title="İleri"><ChevronRight size={16} /></button>
          </>
        )}
      </div>

      <div className="sidebar-content">
        <div className="sidebar-top">
          <button className="brand brand-dropdown" type="button" onClick={() => navigate('/')} title="ImperaOS">
            <span className="brand-text">ImperaOS</span><ChevronDown className="brand-chevron" size={13} />
          </button>
          <button className="icon-button" type="button" onClick={() => setSearchOpen(true)} title="Ara" aria-label="Ara">
            <Search size={14} />
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Ana navigasyon">
          {primaryLinks.map(({ label, icon: Icon, to, trailingIcon: TrailingIcon }) => (
            <NavLink
              key={label}
              to={to}
              end={to === '/'}
              className={({ isActive }) => `sidebar-link ${to === '/' ? 'sidebar-primary-action' : ''} ${isActive ? 'is-active' : ''}`}
            >
              <Icon size={14} strokeWidth={1.75} /><span>{label}</span>
              {TrailingIcon && <TrailingIcon className="sidebar-link-action" size={14} strokeWidth={1.7} />}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-scroll">
          <div hidden={grouping === 'flat'}>
          <div className="sidebar-section-header">
            <span>Projeler</span>
            <div className="sidebar-section-actions">
              <button className={`section-action ${organizeOpen ? 'is-active' : ''}`} type="button" title="Projeleri düzenle" onClick={() => setOrganizeOpen(!organizeOpen)}>
                <MoreHorizontal size={15} />
              </button>
              <button className="section-action" type="button" disabled={busy} title="Yeni proje" onClick={() => void mutate(async () => {
                const project = await productWorkspaceClient.registerProjectFromFolder();
                if (project) startConversation(project.projectId);
              })}>
                <Plus size={16} />
              </button>
            </div>
          </div>
          {organizeOpen && (
            <div className="section-organize-menu" role="menu">
              <label className="section-menu-option">Sıralama
                <select aria-label="Sort projects" value={sort} onChange={(event) => setSort(event.target.value as ProjectSort)}>
                  <option value="manual">El ile</option>
                  <option value="updated_desc">Son güncellenen</option>
                  <option value="priority">Sabitlenenler</option>
                </select>
              </label>
            </div>
          )}
          {error && (
            <p className={`sidebar-error ${error.includes('desktop runtime') ? 'sidebar-runtime-notice' : ''}`} role="alert">
              {error}
            </p>
          )}
          <div className="project-list">
            {projects.map((project) => {
              const projectTasks = activeTasks.filter((task) => task.projectId === project.projectId);
              return (
                <div className="project-group" key={project.projectId}>
                  <SidebarInfoRow className="project-header-row" title={project.title} path={project.rootDisplayName} count={projectTasks.length} pinned={project.pinned}>
                    <button
                      className="project-row"
                      type="button"
                      aria-expanded={Boolean(expanded[project.projectId])}
                      onClick={() => {
                        setExpanded((current) => ({ ...current, [project.projectId]: !current[project.projectId] }));
                      }}
                    >
                      <Folder size={14} strokeWidth={1.75} /><span>{project.title}</span>
                    </button>
                    <button
                      className="section-action project-create-task"
                      type="button"
                      title={`${project.title} projesinde yeni sohbet`}
                      aria-label={`${project.title} projesinde yeni sohbet`}
                      onClick={() => startConversation(project.projectId)}
                    ><SquarePen size={14} /><span>Yeni sohbet</span></button>
                    <SidebarRowActions
                      title={project.title}
                      pinned={project.pinned}
                      busy={busy}
                      canMoveUp={project.manualOrder > 0}
                      onPin={() => void mutate(() => productWorkspaceClient.updateProject(project.projectId, { pinned: !project.pinned }))}
                      onMoveUp={() => void mutate(() => productWorkspaceClient.updateProject(project.projectId, { manualOrder: Math.max(0, project.manualOrder - 1) }))}
                      onArchive={() => void mutate(() => productWorkspaceClient.archiveProject(project.projectId, 'Archived from sidebar'))}
                    />
                  </SidebarInfoRow>
                  {expanded[project.projectId] && projectTasks.length === 0 && <p className="project-empty">Sohbet yok</p>}
                  {expanded[project.projectId] && projectTasks.map((task) => (
                    <SidebarInfoRow key={`${project.projectId}:${task.id}`} title={task.title} projectTitle={project.title} path={project.rootDisplayName} count={projectTasks.length} pinned={Boolean(task.pinned)}>
                      <NavLink
                        className={`project-task ${selectedTaskId === task.id ? 'is-selected' : ''}`}
                        to={`/task/${task.id}`}
                        onClick={() => selectTask(task.id)}
                      >
                        <span className="sidebar-task-title"><span className="sidebar-task-title-track">{task.title}</span></span>
                        {task.status === 'active' && <span className="project-task-dot" />}
                      </NavLink>
                      <SidebarRowActions
                        title={task.title}
                        pinned={Boolean(task.pinned)}
                        busy={busy}
                        canMoveUp={(task.manualOrder ?? 0) > 0}
                        onPin={() => void mutate(async () => {
                          const changed = await productWorkspaceClient.updateTask(task.id, { pinned: !task.pinned });
                          setTaskSort('pinned');
                          upsertTasks([shellTask(changed)]);
                        })}
                        onMoveUp={() => void mutate(async () => {
                          const changed = await productWorkspaceClient.updateTask(task.id, { manualOrder: Math.max(0, (task.manualOrder ?? 0) - 1) });
                          setTaskSort('manual');
                          upsertTasks([shellTask(changed)]);
                        })}
                        onArchive={() => void archiveTask(task.id)}
                      />
                    </SidebarInfoRow>
                  ))}
                </div>
              );
            })}
            {!projects.length && !error && <p className="sidebar-empty">Yönetilen proje eklemek için bir klasör seçin.</p>}
          </div>

          </div>
          <div className="sidebar-section-header recent-section-header">
            <button className="task-section-title" type="button" aria-label="Yakın zamanlılar" aria-expanded={recentExpanded} onClick={() => setRecentExpanded(!recentExpanded)}>
              <span>Yakın zamanlılar</span>{recentExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </button>
            <div className="sidebar-section-actions">
              <button ref={taskMenuAnchor} className="section-action" type="button" aria-label="Görevleri düzenle" title="Görevleri düzenle" aria-expanded={taskControlsOpen} onClick={() => setTaskControlsOpen(!taskControlsOpen)}><MoreHorizontal size={15} /></button>
              <button className="section-action section-create-task" type="button" title="Yeni sohbet" aria-label="Yeni sohbet" onClick={() => startConversation()}><SquarePen size={15} /></button>
            </div>
          </div>
          {taskControlsOpen && <SidebarTaskMenu anchor={taskMenuAnchor} onClose={() => setTaskControlsOpen(false)} grouping={grouping} onGrouping={setGrouping} sort={taskSort} onSort={setTaskSort} onCreateSection={(title) => setSections((current) => [...current, { id: crypto.randomUUID(), title, taskIds: [] }])}><div className="task-collection-controls">
            <button className="task-collection-refresh" type="button" aria-label="Görevleri yenile" disabled={loading || busy} onClick={() => void loadProjects()}><RotateCcw size={14} />{loading ? 'Yenileniyor…' : 'Görevleri yenile'}</button>
            <input aria-label="Görevlerde ara" placeholder="Görevlerde ara…" value={taskQuery} onChange={(event) => setTaskQuery(event.target.value)} />
            <select aria-label="Görev durumu" value={taskFilter} onChange={(event) => setTaskFilter(event.target.value)}>
              <option value="all">Tüm görevler</option><option value="open">Devam edenler</option><option value="awaiting_approval">Onay bekleyenler</option><option value="completed">Tamamlananlar</option><option value="failed">Başarısız olanlar</option><option value="cancelled">İptal edilenler</option>
            </select>
            <select aria-label="Görev sıralaması" value={taskSort} onChange={(event) => setTaskSort(event.target.value)}><option value="recent">Son güncellenen</option><option value="priority">Öncelik</option><option value="pinned">Sabitlenenler önce</option><option value="manual">El ile sıralama</option></select>
          </div></SidebarTaskMenu>}
          {recentExpanded && <>
          {taskError && <p className="sidebar-task-error" role="alert">{taskError}</p>}
          <div className="recent-list" aria-label="Görev listesi" aria-busy={loading}>
            {visibleTasks.map((task) => (
              <SidebarInfoRow key={`recent:${task.id}`} title={task.title} projectTitle={projects.find((project) => project.projectId === task.projectId)?.title} path={projects.find((project) => project.projectId === task.projectId)?.rootDisplayName} count={activeTasks.filter((item) => item.projectId === task.projectId).length} pinned={Boolean(task.pinned)}>
                <NavLink
                  className={`recent-task ${selectedTaskId === task.id ? 'is-current' : ''}`}
                  to={`/task/${task.id}`}
                  onClick={() => selectTask(task.id)}
                >
                  <span className="sidebar-task-title"><span className="sidebar-task-title-track">{task.title}</span></span>
                  {task.status === 'active' && <span className="recent-task-dot" />}
                </NavLink>
                <SidebarRowActions
                  title={task.title}
                  pinned={Boolean(task.pinned)}
                  busy={busy}
                  canMoveUp={(task.manualOrder ?? 0) > 0}
                  onPin={() => void mutate(async () => {
                    const changed = await productWorkspaceClient.updateTask(task.id, { pinned: !task.pinned });
                          setTaskSort('pinned');
                    upsertTasks([shellTask(changed)]);
                  })}
                  onMoveUp={() => void mutate(async () => {
                    const changed = await productWorkspaceClient.updateTask(task.id, { manualOrder: Math.max(0, (task.manualOrder ?? 0) - 1) });
                          setTaskSort('manual');
                    upsertTasks([shellTask(changed)]);
                  })}
                  onArchive={() => void archiveTask(task.id)}
                />
              </SidebarInfoRow>
            ))}
            {!visibleTasks.length && <p className="sidebar-empty recent-empty">{loading ? 'Görevler yükleniyor…' : taskQuery || taskFilter !== 'all' ? 'Bu filtreye uygun görev yok.' : error || taskError ? 'Görevler yüklenemedi. Yenile düğmesiyle tekrar deneyin.' : 'Sohbet yok'}</p>}
          </div>
          </>}
          {sections.map((section) => <section className="sidebar-custom-section" key={section.id} aria-label={section.title}>
            <header><strong>{section.title}</strong><button type="button" aria-label={`${section.title} bölümünü kaldır`} title="Bölümü kaldır (sohbetler korunur)" onClick={() => setSections((current) => current.filter((item) => item.id !== section.id))}>×</button></header>
            {activeTasks.filter((task) => section.taskIds.includes(task.id)).map((task) => <div className="sidebar-custom-task" key={task.id}><NavLink to={`/task/${task.id}`} onClick={() => selectTask(task.id)}>{task.title}</NavLink><button type="button" aria-label={`${task.title} sohbetini bölümden çıkar`} onClick={() => setSections((current) => current.map((item) => item.id === section.id ? { ...item, taskIds: item.taskIds.filter((id) => id !== task.id) } : item))}>×</button></div>)}
            {!activeTasks.some((task) => section.taskIds.includes(task.id)) && <p className="project-empty">Sohbet yok</p>}
            <select aria-label={`${section.title} bölümüne sohbet ekle`} value="" onChange={(event) => { const taskId = event.target.value; if (taskId) setSections((current) => current.map((item) => ({ ...item, taskIds: item.id === section.id ? [...item.taskIds, taskId] : item.taskIds.filter((id) => id !== taskId) }))); }}>
              <option value="">Sohbet ekle…</option>{activeTasks.filter((task) => !section.taskIds.includes(task.id)).map((task) => <option key={task.id} value={task.id}>{task.title}</option>)}
            </select>
          </section>)}
        </div>

        <div className="sidebar-user-wrap">
          <div className="sidebar-user-row">
            <button className="sidebar-user" type="button" onClick={() => setProfileOpen(!profileOpen)}>
              <span className="avatar">IO</span><span className="user-copy"><strong>Operatör</strong><small>ImperaOS</small></span><ChevronDown size={13} />
            </button>
            <button className="icon-button" type="button" onClick={() => navigate('/settings')} title="Ayarlar"><Settings size={14} /></button>
          </div>
          {profileOpen && <div className="user-menu"><button type="button" onClick={() => navigate('/settings')}><Settings size={14} /> Ayarlar</button></div>}
        </div>
      </div>
      {!collapsed && <div className="sidebar-resize" role="separator" aria-label="Kenar çubuğu genişliği" tabIndex={0} onPointerDown={resizeSidebar} />}
    </aside>
  );
}
