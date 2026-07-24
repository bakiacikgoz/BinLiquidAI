import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ProductTask = {
  id: string;
  title: string;
  createdAt: string;
  status: 'active' | 'completed';
  assistantSessionId?: string;
};

type ProductShellState = {
  tasks: ProductTask[];
  selectedTaskId: string | null;
  contextRailOpen: boolean;
  dockOpen: boolean;
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  theme: 'dark' | 'light';
  createTask: (title: string) => ProductTask;
  upsertTasks: (tasks: ProductTask[]) => void;
  selectTask: (taskId: string | null) => void;
  setContextRailOpen: (open: boolean) => void;
  setDockOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSidebarWidth: (width: number) => void;
  setTheme: (theme: 'dark' | 'light') => void;
};

function taskId(): string {
  return `task-${globalThis.crypto?.randomUUID?.() ?? Date.now().toString(36)}`;
}

/** UI-only navigation state. Product records are deliberately not fabricated here. */
export const useProductShellStore = create<ProductShellState>()(persist((set) => ({
  tasks: [],
  selectedTaskId: null,
  contextRailOpen: true,
  dockOpen: false,
  sidebarCollapsed: false,
  sidebarWidth: 260,
  theme: 'dark',
  createTask: (title) => {
    const task: ProductTask = {
      id: taskId(),
      title: title.trim() || 'Untitled work',
      createdAt: new Date().toISOString(),
      status: 'active',
    };
    set((state) => ({ tasks: [task, ...state.tasks], selectedTaskId: task.id }));
    return task;
  },
  upsertTasks: (tasks) => set((state) => {
    const next = new Map(state.tasks.map((task) => [task.id, task]));
    tasks.forEach((task) => next.set(task.id, task));
    return { tasks: [...next.values()].sort((left, right) => right.createdAt.localeCompare(left.createdAt)) };
  }),
  selectTask: (selectedTaskId) => set({ selectedTaskId }),
  setContextRailOpen: (contextRailOpen) => set({ contextRailOpen }),
  setDockOpen: (dockOpen) => set({ dockOpen }),
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
  setSidebarWidth: (sidebarWidth) => set({ sidebarWidth: Math.min(420, Math.max(220, sidebarWidth)) }),
  setTheme: (theme) => set({ theme }),
}), {
  name: 'imperaos-product-shell-preferences-v2',
  // Tasks and conversations remain owned by the future Product Workspace domain,
  // never by this UI preference store.
  partialize: (state) => ({
    contextRailOpen: state.contextRailOpen,
    dockOpen: state.dockOpen,
    sidebarCollapsed: state.sidebarCollapsed,
    sidebarWidth: state.sidebarWidth,
    theme: state.theme,
  }),
}));
