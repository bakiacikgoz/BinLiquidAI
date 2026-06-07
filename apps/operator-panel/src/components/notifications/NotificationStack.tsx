import { Icon } from '../primitives/Icon';

export type NotificationKind = 'info' | 'success' | 'warning' | 'error';

export type NotificationItem = {
  id: string;
  kind: NotificationKind;
  title: string;
  subtitle: string;
  time: string;
};

const iconForKind: Record<NotificationKind, 'activity' | 'check' | 'alert' | 'reject'> = {
  info: 'activity',
  success: 'check',
  warning: 'alert',
  error: 'reject',
};

export function NotificationStack({
  items,
  onDismiss,
}: {
  items: NotificationItem[];
  onDismiss: (id: string) => void;
}) {
  const visibleItems = items.slice(0, 2);
  const hiddenCount = Math.max(0, items.length - visibleItems.length);
  return (
    <div className="notification-stack" aria-label="Bildirimler">
      {visibleItems.map((item) => (
        <div className={`notification-item notification-item-${item.kind}`} key={item.id}>
          <span className="notification-icon">
            <Icon name={iconForKind[item.kind]} />
          </span>
          <div>
            <strong>{item.title}</strong>
            <p>{item.subtitle}</p>
          </div>
          <time>{item.time}</time>
          <button type="button" aria-label="Bildirimi kapat" onClick={() => onDismiss(item.id)}>
            <Icon name="close" />
          </button>
        </div>
      ))}
      {hiddenCount > 0 ? <div className="notification-summary">{hiddenCount} sistem bildirimi daha</div> : null}
    </div>
  );
}
