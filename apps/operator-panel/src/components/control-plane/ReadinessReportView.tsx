export function ReadinessReportView({ report }: { report: unknown }) {
  return <pre className="json-panel">{JSON.stringify(report ?? {}, null, 2)}</pre>;
}
