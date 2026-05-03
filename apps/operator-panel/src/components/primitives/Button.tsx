import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  icon?: ReactNode;
  variant?: ButtonVariant;
};

export function Button({ children, icon, variant = 'secondary', className = '', ...props }: ButtonProps) {
  return (
    <button className={`mc-button mc-button-${variant} ${className}`.trim()} type="button" {...props}>
      {icon ? <span className="mc-button-icon">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
}
