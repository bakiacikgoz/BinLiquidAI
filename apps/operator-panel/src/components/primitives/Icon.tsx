export type IconName =
  | 'activity'
  | 'alert'
  | 'approval'
  | 'archive'
  | 'arrow-up'
  | 'bell'
  | 'box'
  | 'check'
  | 'chevron'
  | 'clipboard'
  | 'close'
  | 'command'
  | 'copy'
  | 'download'
  | 'edit'
  | 'eye'
  | 'gauge'
  | 'grid'
  | 'health'
  | 'hex'
  | 'home'
  | 'layers'
  | 'list'
  | 'logs'
  | 'menu'
  | 'monitor'
  | 'moon'
  | 'more'
  | 'paperclip'
  | 'play'
  | 'policy'
  | 'refresh'
  | 'reject'
  | 'report'
  | 'settings'
  | 'share'
  | 'shield'
  | 'send'
  | 'sparkle'
  | 'sun'
  | 'target'
  | 'terminal'
  | 'user'
  | 'users';

const paths: Record<IconName, string> = {
  activity: 'M4 12h3l2-6 4 12 2-6h5',
  alert: 'M12 4l8 15H4L12 4z M12 9v4 M12 16h.01',
  approval: 'M12 3l7 4v5c0 4.4-2.8 7.4-7 9-4.2-1.6-7-4.6-7-9V7z M9 12l2 2 4-5',
  archive: 'M4 7h16 M6 7v12h12V7 M9 11h6',
  'arrow-up': 'M12 18V6 M6.75 11.25 12 6l5.25 5.25',
  bell: 'M6 15h12l-1.5-2V9a4.5 4.5 0 0 0-9 0v4L6 15z M10 19h4',
  box: 'M4 8l8-4 8 4-8 4-8-4z M4 8v8l8 4 8-4V8 M12 12v8',
  check: 'M5 12l4 4L19 6',
  chevron: 'M9 6l6 6-6 6',
  clipboard: 'M8 5h8v3H8z M6 7H5v13h14V7h-1',
  close: 'M6 6l12 12M18 6L6 18',
  command: 'M9 6V5a3 3 0 1 0-3 3h1v8H6a3 3 0 1 0 3 3v-1h6v1a3 3 0 1 0 3-3h-1V8h1a3 3 0 1 0-3-3v1H9z M9 8h6v8H9z',
  copy: 'M9 9h10v10H9z M5 5h10v10',
  download: 'M12 4v10 M8 10l4 4 4-4 M5 19h14',
  edit: 'M5 19l4-.8L18 9l-3-3-9 9-.8 4z M13 7l3 3',
  eye: 'M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  gauge: 'M4 14a8 8 0 1 1 16 0 M12 14l4-4 M7 18h10',
  grid: 'M5 5h6v6H5z M13 5h6v6h-6z M5 13h6v6H5z M13 13h6v6h-6z',
  health: 'M12 21s-7-4.4-7-10a4 4 0 0 1 7-2.7A4 4 0 0 1 19 11c0 5.6-7 10-7 10z',
  hex: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z M12 7.5l4 2.3v4.4l-4 2.3-4-2.3V9.8l4-2.3z M12 7.5v9',
  home: 'M4 11l8-7 8 7v9h-5v-6H9v6H4z',
  layers: 'M12 4l8 4-8 4-8-4 8-4z M4 12l8 4 8-4 M4 16l8 4 8-4',
  list: 'M8 6h12 M8 12h12 M8 18h12 M4 6h.01 M4 12h.01 M4 18h.01',
  logs: 'M7 4h10l3 3v13H7z M17 4v4h4 M10 12h7 M10 16h7',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  monitor: 'M4 5h16v11H4z M8 20h8 M12 16v4',
  moon: 'M20 14.5A7.5 7.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z',
  more: 'M5 12h.01 M12 12h.01 M19 12h.01',
  paperclip: 'M21 11l-8.5 8.5a5 5 0 0 1-7-7L14 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-2.8-2.8L15 7.4',
  play: 'M8 5l11 7-11 7z',
  policy: 'M12 3l7 3v6c0 4-2.8 7.2-7 9-4.2-1.8-7-5-7-9V6z M9 12l2 2 4-5',
  refresh: 'M20 6v5h-5 M4 18v-5h5 M18 10a6 6 0 0 0-10-3L4 11 M6 14a6 6 0 0 0 10 3l4-4',
  reject: 'M6 6l12 12M18 6L6 18 M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  report: 'M6 4h12v16H6z M9 8h6 M9 12h6 M9 16h4',
  settings: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M12 2v3 M12 19v3 M4.9 4.9l2.1 2.1 M17 17l2.1 2.1 M2 12h3 M19 12h3 M4.9 19.1L7 17 M17 7l2.1-2.1',
  share: 'M12 16V4 M7 9l5-5 5 5 M5 16v4h14v-4',
  shield: 'M12 3l8 4v5c0 5-3.4 8-8 9-4.6-1-8-4-8-9V7z M12 8v5 M12 16h.01',
  send: 'M4 4l17 8-17 8 4-8-4-8z M8 12h13',
  sparkle: 'M12 3l1.5 5.2L19 10l-5.5 1.8L12 17l-1.5-5.2L5 10l5.5-1.8L12 3z M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M12 2v3 M12 19v3 M4.2 4.2l2.1 2.1 M17.7 17.7l2.1 2.1 M2 12h3 M19 12h3 M4.2 19.8l2.1-2.1 M17.7 6.3l2.1-2.1',
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
