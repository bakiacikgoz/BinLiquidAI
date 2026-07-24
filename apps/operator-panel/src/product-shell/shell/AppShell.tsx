import type { ReactNode } from 'react';

import { Sidebar } from './Sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  return <main className="imperaos-product-shell-v2"><Sidebar /><section className="ps-main">{children}</section></main>;
}
