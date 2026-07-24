import type { ReactNode } from 'react';

import { Sidebar } from './Sidebar';
import { useProductShellStore } from '../state/productShellStore';

export function AppShell({ children }: { children: ReactNode }) {
  const theme = useProductShellStore((state) => state.theme);
  const sidebarWidth = useProductShellStore((state) => state.sidebarWidth);
  const sidebarCollapsed = useProductShellStore((state) => state.sidebarCollapsed);
  return <main className={`imperaos-product-shell-v2 ps-theme-${theme}`} style={{ gridTemplateColumns: sidebarCollapsed ? '64px minmax(0, 1fr)' : `${sidebarWidth}px minmax(0, 1fr)` }}><Sidebar /><section className="ps-main">{children}</section></main>;
}
