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

export type SessionEventFilter = 'all' | 'status' | 'approval' | 'warning' | 'error' | 'computer_use' | 'assistant';

const EVENT_FILTER_OPTIONS: Array<{ value: SessionEventFilter; label: string }> = [
  { value: 'all', label: 'Tümü' },
  { value: 'status', label: 'Status' },
  { value: 'approval', label: 'Approval' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'computer_use', label: 'Computer-use' },
  { value: 'assistant', label: 'Assistant' },
];

export function SessionEventsCard({
  items,
  filter = 'all',
  hasMore = false,
  loadingMore = false,
  onFilterChange,
  onLoadMore,
}: {
  items: SessionEventItem[];
  filter?: SessionEventFilter;
  hasMore?: boolean;
  loadingMore?: boolean;
  onFilterChange?: (filter: SessionEventFilter) => void;
  onLoadMore?: () => void;
}) {
  return (
    <div className="mc-card session-events-card">
      <SectionHeader
        title="OTURUM OLAYLARI"
        action={
          <label className="filter-button session-event-filter">
            <select
              aria-label="Oturum olay filtresi"
              value={filter}
              disabled={!onFilterChange}
              title={!onFilterChange ? 'Event filtering is not available for this view' : undefined}
              data-disabled-reason={!onFilterChange ? 'Event filtering is not available for this view' : undefined}
              onChange={(event) => onFilterChange?.(event.target.value as SessionEventFilter)}
            >
              {EVENT_FILTER_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <Icon name="chevron" />
          </label>
        }
      />
      <div className="session-event-list">
        {items.length > 0 ? (
          items.map((item) => (
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
          ))
        ) : (
          <p className="session-event-empty">Bu filtre için olay yok.</p>
        )}
      </div>
      <Button
        variant="ghost"
        className="load-more-button"
        icon={<Icon name="chevron" />}
        disabled={!hasMore || !onLoadMore || loadingMore}
        title={!hasMore || !onLoadMore ? 'No additional events are available' : undefined}
        onClick={onLoadMore}
      >
        {loadingMore ? 'Yükleniyor' : 'Daha fazla olay yükle'}
      </Button>
    </div>
  );
}
