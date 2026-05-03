import { Card } from '../primitives/Card';
import { ProgressBar } from '../primitives/ProgressBar';
import { StatusDot } from '../primitives/StatusDot';

export function RunStatusCard({
  status,
  error,
  stage,
  startedAt,
  duration,
  progress,
}: {
  status: string;
  error: string;
  stage: string;
  startedAt: string;
  duration: string;
  progress: number;
}) {
  return (
    <Card className="run-status-card">
      <div className="run-status-primary">
        <span className="mc-kicker">ÇALIŞTIRMA DURUMU</span>
        <strong className="run-status-code">
          {status} <StatusDot tone="error" />
        </strong>
        <p>{error}</p>
      </div>
      <div className="run-status-stage">
        <span className="mc-kicker">AŞAMA</span>
        <div className="run-progress-row">
          <span>{stage}</span>
          <ProgressBar value={progress} />
          <strong>{Math.round(progress)}%</strong>
        </div>
        <dl>
          <div>
            <dt>BAŞLADI</dt>
            <dd>{startedAt}</dd>
          </div>
          <div>
            <dt>SÜRE</dt>
            <dd>{duration}</dd>
          </div>
        </dl>
      </div>
    </Card>
  );
}
