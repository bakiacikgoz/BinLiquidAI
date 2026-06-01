import { RawInspector } from './RawInspector';

export function ReadinessReportView({ report }: { report: unknown }) {
  return <RawInspector value={report} label="Readiness report raw payload" />;
}
