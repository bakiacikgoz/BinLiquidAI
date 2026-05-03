export type IconName =
  | 'activity'
  | 'alert'
  | 'archive'
  | 'bell'
  | 'box'
  | 'check'
  | 'chevron'
  | 'clipboard'
  | 'close'
  | 'copy'
  | 'download'
  | 'edit'
  | 'gauge'
  | 'grid'
  | 'health'
  | 'hex'
  | 'home'
  | 'layers'
  | 'list'
  | 'logs'
  | 'play'
  | 'policy'
  | 'refresh'
  | 'reject'
  | 'report'
  | 'settings'
  | 'shield'
  | 'target'
  | 'terminal'
  | 'user'
  | 'users';

const paths: Record<IconName, string> = {
  activity: 'M4 12h3l2-6 4 12 2-6h5',
  alert: 'M12 4l8 15H4L12 4z M12 9v4 M12 16h.01',
  archive: 'M4 7h16 M6 7v12h12V7 M9 11h6',
  bell: 'M6 15h12l-1.5-2V9a4.5 4.5 0 0 0-9 0v4L6 15z M10 19h4',
  box: 'M4 8l8-4 8 4-8 4-8-4z M4 8v8l8 4 8-4V8 M12 12v8',
  check: 'M5 12l4 4L19 6',
  chevron: 'M9 6l6 6-6 6',
  clipboard: 'M8 5h8v3H8z M6 7H5v13h14V7h-1',
  close: 'M6 6l12 12M18 6L6 18',
  copy: 'M9 9h10v10H9z M5 5h10v10',
  download: 'M12 4v10 M8 10l4 4 4-4 M5 19h14',
  edit: 'M5 19l4-.8L18 9l-3-3-9 9-.8 4z M13 7l3 3',
  gauge: 'M4 14a8 8 0 1 1 16 0 M12 14l4-4 M7 18h10',
  grid: 'M5 5h6v6H5z M13 5h6v6h-6z M5 13h6v6H5z M13 13h6v6h-6z',
  health: 'M12 21s-7-4.4-7-10a4 4 0 0 1 7-2.7A4 4 0 0 1 19 11c0 5.6-7 10-7 10z',
  hex: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 7.5l4 2.3v4.4l-4 2.3-4-2.3V9.8l4-2.3z M12 7.5v9',
  home: 'M4 11l8-7 8 7v9h-5v-6H9v6H4z',
  layers: 'M12 4l8 4-8 4-8-4 8-4z M4 12l8 4 8-4 M4 16l8 4 8-4',
  list: 'M8 6h12 M8 12h12 M8 18h12 M4 6h.01 M4 12h.01 M4 18h.01',
  logs: 'M7 4h10l3 3v13H7z M17 4v4h4 M10 12h7 M10 16h7',
  play: 'M8 5l11 7-11 7z',
  policy: 'M12 3l7 3v6c0 4-2.8 7.2-7 9-4.2-1.8-7-5-7-9V6z M9 12l2 2 4-5',
  refresh: 'M20 6v5h-5 M4 18v-5h5 M18 10a6 6 0 0 0-10-3L4 11 M6 14a6 6 0 0 0 10 3l4-4',
  reject: 'M6 6l12 12M18 6L6 18 M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  report: 'M6 4h12v16H6z M9 8h6 M9 12h6 M9 16h4',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M12 2v3 M12 19v3 M4.9 4.9l2.1 2.1 M17 17l2.1 2.1 M2 12h3 M19 12h3 M4.9 19.1L7 17 M17 7l2.1-2.1',
  shield: 'M12 3l8 4v5c0 5-3.4 8-8 9-4.6-1-8-4-8-9V7z M12 8v5 M12 16h.01',
  target: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2z M16 4l-4 4',
  terminal: 'M4 5h16v14H4z M8 9l3 3-3 3 M12 15h4',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0',
  users: 'M9 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M2 21a7 7 0 0 1 14 0 M17 11a3 3 0 1 0 0-6 M16 18a5 5 0 0 1 5 3',
};

export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return (
    <svg className={`mc-icon ${className}`.trim()} viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[name]} />
    </svg>
  );
}
