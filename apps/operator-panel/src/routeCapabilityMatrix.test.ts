import { describe, expect, it } from 'vitest';

import { routes } from './routeRegistry';
import { routeCapabilityMatrix } from './routeCapabilityMatrix';

describe('routeCapabilityMatrix', () => {
  it('covers every visible route exactly once', () => {
    const routeIds = routes.map((route) => route.routeId);
    const matrixRouteIds = routeCapabilityMatrix.map((route) => route.routeId);

    expect(new Set(matrixRouteIds).size).toBe(matrixRouteIds.length);
    expect(matrixRouteIds.sort()).toEqual([...routeIds].sort());
  });

  it('classifies primary actions with executable commands or disabled reasons', () => {
    for (const route of routeCapabilityMatrix) {
      expect(route.title).toBeTruthy();
      expect(['bridge', 'snapshot', 'preview_only']).toContain(route.dataSource);
      for (const action of route.primaryActions) {
        expect(['working', 'disabled_with_reason', 'preview_only']).toContain(action.state);
        expect(action.noShipIfInert).toBe(true);
        if (action.state === 'working') {
          expect(action.bridgeCommand || action.cliCommand).toBeTruthy();
        }
        if (action.state === 'disabled_with_reason') {
          expect(action.disabledReasonCode).toMatch(/^[A-Z0-9_]+$/);
        }
      }
    }
  });
});
