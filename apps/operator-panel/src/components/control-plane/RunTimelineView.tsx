export function RunTimelineView({ runs }: { runs: unknown }) {
  return <pre className="json-panel">{JSON.stringify(runs ?? {}, null, 2)}</pre>;
}
