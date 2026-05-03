import { Icon } from '../primitives/Icon';
import { SectionHeader } from '../primitives/SectionHeader';
import { StatusDot } from '../primitives/StatusDot';

export type ActivityItem = {
  id: string;
  time: string;
  title: string;
  body: string;
  tone: 'info' | 'success' | 'warning' | 'neutral';
};

const toneIcon: Record<ActivityItem['tone'], 'activity' | 'check' | 'archive' | 'play'> = {
  info: 'activity',
  success: 'check',
  warning: 'archive',
  neutral: 'play',
};

export function LiveAgentActivity({ items }: { items: ActivityItem[] }) {
  return (
    <div className="mc-card live-agent-card">
      <SectionHeader
        title="CANLI AJAN ETKİNLİĞİ"
        action={
          <span className="live-label">
            <StatusDot tone="success" pulse /> CANLI
          </span>
        }
      />
      <div className="live-agent-list">
        {items.map((item) => (
          <div className={`live-agent-row live-agent-row-${item.tone}`} key={item.id}>
            <span className="live-agent-line" />
            <span className="live-agent-icon">
              <Icon name={toneIcon[item.tone]} />
            </span>
            <time>{item.time}</time>
            <div>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
