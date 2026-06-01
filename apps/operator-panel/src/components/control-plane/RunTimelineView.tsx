import { RawInspector } from './RawInspector';

export function RunTimelineView({ runs }: { runs: unknown }) {
  return <RawInspector value={runs} label="Run timeline raw payload" />;
}
