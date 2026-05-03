import type { HTMLAttributes, ReactNode } from 'react';

type CardProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
  elevated?: boolean;
};

export function Card({ children, className = '', elevated = false, ...props }: CardProps) {
  return (
    <article className={`mc-card${elevated ? ' mc-card-elevated' : ''} ${className}`.trim()} {...props}>
      {children}
    </article>
  );
}
