import type { TargetEvidenceClosureSummary } from '../control-plane/types';

export type { TargetEvidenceClosureSummary };

export type TargetEvidenceBadge = {
  label: string;
  tone: 'ready' | 'warning' | 'blocked' | 'neutral';
};
