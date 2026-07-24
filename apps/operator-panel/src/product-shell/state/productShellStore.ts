import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ProductTask = {
  id: string;
  title: string;
  createdAt: string;
  status: 'draft' | 'active' | 'awaiting_approval' | 'completed' | 'failed' | 'cancelled' | 'archived';
  assistantSessionId?: string;
  reasoningEffort?: 'low' | 'medium' | 'high' | 'very_high';
  speedProfile?: 'standard' | 'fast';
  approvalProfile?: 'always_ask' | 'risk_based' | 'policy_automatic';
};

type ProductShellState = {
  tasks: ProductTask[];
  selectedTaskId: string | null;
  contextRailOpen: boolean;
  dockOpen: boolean;
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  theme: 'dark' | 'light';
  upsertTasks: (tasks: ProductTask[]) => void;
  selectTask: (taskId: string | null) => void;
  setContextRailOpen: (open: boolean) => void;
  setDockOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSidebarWidth: (width: number) => void;
  setTheme: (theme: 'dark' | 'light') => void;
};

/** UI-only navigation state. Product records are deliberately not fabricated here. */
export const useProductShellStore = create<ProductShellState>()(persist((set) => ({
  tasks: [],
  selectedTaskId: null,
  contextRailOpen: true,
  dockOpen: false,
  sidebarCollapsed: false,
  sidebarWidth: 260,
  theme: 'dark',
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
