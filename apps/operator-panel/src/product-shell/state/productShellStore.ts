import { create } from 'zustand';

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
  createTask: (title: string) => ProductTask;
  selectTask: (taskId: string | null) => void;
  setContextRailOpen: (open: boolean) => void;
  setDockOpen: (open: boolean) => void;
};

function taskId(): string {
  return `task-${globalThis.crypto?.randomUUID?.() ?? Date.now().toString(36)}`;
}

/** UI-only navigation state. Product records are deliberately not fabricated here. */
export const useProductShellStore = create<ProductShellState>((set) => ({
  tasks: [],
  selectedTaskId: null,
  contextRailOpen: true,
  dockOpen: false,
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
  selectTask: (selectedTaskId) => set({ selectedTaskId }),
  setContextRailOpen: (contextRailOpen) => set({ contextRailOpen }),
  setDockOpen: (dockOpen) => set({ dockOpen }),
}));
