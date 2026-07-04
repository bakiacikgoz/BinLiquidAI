export type OperatorTone = 'neutral' | 'success' | 'warning' | 'error' | 'info' | 'muted';

export function operatorToneFromStatus(status: string): OperatorTone {
  const normalized = status.toLowerCase();
  if (/(ready|active|enabled|clear|passed|healthy|validated|available|complete|success)/.test(normalized)) {
    return 'success';
  }
  if (/(blocked|failed|deny|error|missing|required|rejected|unsafe)/.test(normalized)) {
    return 'error';
  }
  if (/(conditional|warning|pending|approval|draft|stale|guarded)/.test(normalized)) {
    return 'warning';
  }
  if (/(empty|unknown|not run|none)/.test(normalized)) {
    return 'muted';
  }
  return 'info';
}
