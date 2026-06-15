import type { MainlineRcFreezeSnapshot } from '../control-plane/types';

export type { MainlineRcFreezeSnapshot };

export type MainlineRcFreezeBadge = {
  label: string;
  tone: 'ready' | 'warning' | 'blocked' | 'neutral';
};
