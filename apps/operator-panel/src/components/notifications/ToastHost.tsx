import { Icon } from '../primitives/Icon';

export type ToastItem = {
  id: number;
  kind: 'ok' | 'error';
  text: string;
};

export function ToastHost({ toasts }: { toasts: ToastItem[] }) {
  return (
    <div className="toast-zone">
      {toasts.map((toast) => (
        <div className={toast.kind === 'error' ? 'toast toast-error' : 'toast'} key={toast.id}>
          <Icon name={toast.kind === 'error' ? 'reject' : 'check'} />
          <span>{toast.text}</span>
        </div>
      ))}
    </div>
  );
}
