export type StatusTone = 'success' | 'warning' | 'error' | 'info' | 'muted';

export function StatusDot({ tone = 'muted', pulse = false }: { tone?: StatusTone; pulse?: boolean }) {
  return <span className={`mc-status-dot mc-status-dot-${tone}${pulse ? ' mc-status-dot-pulse' : ''}`} />;
}
