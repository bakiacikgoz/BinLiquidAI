import { Card } from '../primitives/Card';
import { Icon } from '../primitives/Icon';
import { StatusDot } from '../primitives/StatusDot';

export function MissionObjectiveCard({
  objective,
  priority,
  targetType,
}: {
  objective: string;
  priority: string;
  targetType: string;
}) {
  return (
    <Card className="mission-objective-card">
      <div className="mission-target-mark">
        <Icon name="target" />
      </div>
      <div className="mission-objective-copy">
        <span className="mc-kicker">GEÇERLİ HEDEF</span>
        <h2>{objective}</h2>
        <p>Konuşma aktif ise, bağlama ve onaylara bağlı kalır.</p>
      </div>
      <div className="mission-objective-meta">
        <div>
          <span>ÖNCELİK</span>
          <strong>
            <StatusDot tone="error" /> {priority}
          </strong>
        </div>
        <div>
          <span>HEDEF TİPİ</span>
          <strong>{targetType}</strong>
        </div>
      </div>
    </Card>
  );
}
