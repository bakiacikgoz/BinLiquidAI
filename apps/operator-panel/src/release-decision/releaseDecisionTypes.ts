import type { RcReleaseDecisionSnapshot } from '../control-plane/types';

export type { RcReleaseDecisionSnapshot };

export type ReleaseDecisionBadge = {
  label: string;
  tone: 'good' | 'warn' | 'danger' | 'muted';
};
