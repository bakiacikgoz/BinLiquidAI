import type { DesignPartnerFieldEvidenceSnapshot } from '../control-plane/types';

export type { DesignPartnerFieldEvidenceSnapshot };

export type FieldEvidenceBadge = {
  label: string;
  tone: 'ready' | 'warning' | 'blocked' | 'neutral';
};
