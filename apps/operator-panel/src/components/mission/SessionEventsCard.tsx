import { Badge } from '../primitives/Badge';
import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';
import { SectionHeader } from '../primitives/SectionHeader';

export type SessionEventItem = {
  id: string;
  time: string;
  title: string;
  body: string;
  tag: string;
  tone: 'info' | 'success' | 'warning' | 'neutral';
};

export function SessionEventsCard({ items }: { items: SessionEventItem[] }) {
  return (
    <div className="mc-card session-events-card">
      <SectionHeader
        title="OTURUM OLAYLARI"
        action={
          <button className="filter-button" type="button">
            Tümü <Icon name="chevron" />
          </button>
        }
      />
      <div className="session-event-list">
        {items.map((item) => (
          <div className="session-event-row" key={item.id}>
            <time>{item.time}</time>
            <div>
              <strong>{item.title}</strong>
              <p>{item.body}</p>
            </div>
            <Badge tone={item.tone === 'success' ? 'success' : item.tone === 'warning' ? 'warning' : 'info'}>
              {item.tag}
            </Badge>
          </div>
        ))}
      </div>
      <Button variant="ghost" className="load-more-button" icon={<Icon name="chevron" />}>
        Daha fazla olay yükle
      </Button>
    </div>
  );
}
