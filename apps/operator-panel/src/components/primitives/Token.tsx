import type { ReactNode } from 'react';

type TokenTone = 'neutral' | 'success' | 'warning' | 'error' | 'info' | 'muted';

function tokenClass(base: string, tone: TokenTone, className = ''): string {
  return [base, `${base}-${tone}`, className].filter(Boolean).join(' ');
}

export function CodeToken({
  children,
  className,
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <span className={tokenClass('code-token', 'neutral', className)} title={title}>
      {children}
    </span>
  );
}

export function ReasonChip({
  children,
  tone = 'warning',
  title,
}: {
  children: ReactNode;
  tone?: TokenTone;
  title?: string;
}) {
  return (
    <span className={tokenClass('reason-chip', tone)} title={title}>
      {children}
    </span>
  );
}

export function StatusBadge({
  children,
  tone = 'neutral',
  title,
}: {
  children: ReactNode;
  tone?: TokenTone;
  title?: string;
}) {
  return (
    <span className={tokenClass('status-badge', tone)} title={title}>
      {children}
    </span>
  );
}
