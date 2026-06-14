import type { DesignPartnerHandoffSnapshot } from '../control-plane/types';

export type { DesignPartnerHandoffSnapshot };

export type HandoffBadge = {
  label: string;
  tone: 'ready' | 'warning' | 'blocked' | 'neutral';
};
