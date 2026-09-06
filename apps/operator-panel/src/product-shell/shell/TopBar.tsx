import {
  Folder,
  ChevronLeft,
  ChevronRight,
  PanelBottomOpen,
  PanelLeftOpen,
  PanelRightOpen,
  Plus,
  SlidersHorizontal,
  SquarePen,
} from 'lucide-react';
import { useLocation, useNavigate, useMatch } from 'react-router-dom';

import { TaskMenu } from './TaskMenu';
import { useProductShellStore } from '../state/productShellStore';

export function TopBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const taskMatch = useMatch('/task/:taskId/*');
  const taskId = taskMatch?.params.taskId;
  const task = useProductShellStore((state) => state.tasks.find((item) => item.id === taskId));
  const sidebarCollapsed = useProductShellStore((state) => state.sidebarCollapsed);
  const setSidebarCollapsed = useProductShellStore((state) => state.setSidebarCollapsed);
  const contextRailOpen = useProductShellStore((state) => state.contextRailOpen);
  const setContextRailOpen = useProductShellStore((state) => state.setContextRailOpen);
  const dockOpen = useProductShellStore((state) => state.dockOpen);
  const setDockOpen = useProductShellStore((state) => state.setDockOpen);
  const isWorkspace = location.pathname.endsWith('/workspace');

  if (sidebarCollapsed) {
    return (
      <header data-tauri-drag-region className="topbar closed-panels-topbar">
        <div className="closed-panels-leading">
          <button className="icon-button" type="button" onClick={() => setSidebarCollapsed(false)} title="Kenar çubuğunu aç" aria-label="Kenar çubuğunu aç">
            <PanelLeftOpen size={18} />
          </button>
          <button className="icon-button subdued" type="button" onClick={() => navigate(-1)} title="Geri">
            <ChevronLeft size={18} />
          </button>
          <button className="icon-button subdued" type="button" onClick={() => navigate(1)} title="İleri">
            <ChevronRight size={18} />
          </button>
          <button className="icon-button closed-panels-new-work" type="button" onClick={() => navigate('/')} title="Yeni görev">
            <SquarePen size={17} />
          </button>
        </div>
        {task && <div className="task-header-title"><Folder size={15}/><span className="task-crumb">{task.title}</span><TaskMenu task={task}/></div>}
        <div className="closed-panels-actions">
          {taskId ? <>
              <button className={`icon-button ${contextRailOpen ? 'is-active' : ''}`} type="button" onClick={() => setContextRailOpen(!contextRailOpen)} title="Sabitlenmiş özeti aç/kapat"><SlidersHorizontal size={17}/></button>
              <button className={`icon-button ${dockOpen ? 'is-active' : ''}`} type="button" onClick={() => setDockOpen(!dockOpen)} title="Terminal paneli">
                <PanelBottomOpen size={17} />
              </button>
              <button className={`icon-button ${isWorkspace ? 'is-active' : ''}`} type="button" onClick={() => navigate(isWorkspace ? `/task/${taskId}` : `/task/${taskId}/workspace`)} title="Çalışma alanı">
                <PanelRightOpen size={17} />
              </button>
            </> : <>
              <span className="icon-button" aria-disabled="true" title="Alt panel bir görev açıldığında kullanılabilir." data-disabled-reason="TASK_CONTEXT_REQUIRED"><PanelBottomOpen size={17} /></span>
              <span className="icon-button" aria-disabled="true" title="Bağlam paneli bir görev açıldığında kullanılabilir." data-disabled-reason="TASK_CONTEXT_REQUIRED"><PanelRightOpen size={17} /></span>
            </>}
        </div>
      </header>
    );
  }

  return (
    <header data-tauri-drag-region className={`topbar ${taskId ? 'task-reference-header' : ''}`}>
      <div className="topbar-leading task-header-title">
        <Folder size={15} aria-hidden="true" />
        <span className="task-crumb">{task?.title ?? 'ImperaOS'}</span>{task && <TaskMenu task={task}/>}
      </div>
      <div className="topbar-actions task-header-actions">
        <button className="topbar-new" type="button" onClick={() => navigate('/')}>
          <Plus size={15} /> Yeni görev
        </button>
        {taskId && <>
          <button className={`icon-button ${contextRailOpen ? 'is-active' : ''}`} type="button" onClick={() => setContextRailOpen(!contextRailOpen)} title="Sabitlenmiş özeti aç/kapat" aria-pressed={contextRailOpen}><SlidersHorizontal size={16}/></button>
          <button className={`icon-button ${dockOpen ? 'is-active' : ''}`} type="button" onClick={() => setDockOpen(!dockOpen)} title="Terminal paneli" aria-pressed={dockOpen}><PanelBottomOpen size={16}/></button>
          <button className={`icon-button ${isWorkspace ? 'is-active' : ''}`} type="button" onClick={() => navigate(isWorkspace ? `/task/${taskId}` : `/task/${taskId}/workspace`)} title="Çalışma alanı" aria-pressed={isWorkspace}><PanelRightOpen size={16}/></button>
        </>}
      </div>
    </header>
  );
}
