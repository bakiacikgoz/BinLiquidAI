import { beforeEach, describe, expect, it } from 'vitest';

import {
  migrateProductShellPreferences,
  useProductShellStore,
} from './productShellStore';

describe('product shell sidebar preferences', () => {
  beforeEach(() => {
    localStorage.clear();
    useProductShellStore.setState(useProductShellStore.getInitialState(), true);
  });

  it('starts at the approved 260px sidebar proportion', () => {
    expect(useProductShellStore.getState().sidebarWidth).toBe(260);
  });

  it('keeps live resizing inside the usable 220px to 340px range', () => {
    useProductShellStore.getState().setSidebarWidth(180);
    expect(useProductShellStore.getState().sidebarWidth).toBe(220);

    useProductShellStore.getState().setSidebarWidth(380);
    expect(useProductShellStore.getState().sidebarWidth).toBe(340);
  });

  it('preserves valid persisted widths and resets oversized legacy widths', () => {
    expect(migrateProductShellPreferences({ sidebarWidth: 286, theme: 'dark' }, 2)).toEqual({
      sidebarWidth: 286,
      theme: 'dark',
    });
    expect(migrateProductShellPreferences({ sidebarWidth: 414, theme: 'dark' }, 2)).toEqual({
      sidebarWidth: 260,
      theme: 'dark',
    });
  });
});
