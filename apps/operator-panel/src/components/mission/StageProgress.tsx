import { Icon } from '../primitives/Icon';

export type MissionStageKey = 'planning' | 'preparing' | 'running' | 'approval' | 'done';

const stages: Array<{ key: MissionStageKey; label: string; icon: 'clipboard' | 'layers' | 'play' | 'check' }> = [
  { key: 'planning', label: 'Planlama', icon: 'clipboard' },
  { key: 'preparing', label: 'Hazırlık', icon: 'layers' },
  { key: 'running', label: 'Çalıştırma', icon: 'play' },
  { key: 'approval', label: 'Onay', icon: 'check' },
  { key: 'done', label: 'Tamamlandı', icon: 'check' },
];

export function StageProgress({ currentStage }: { currentStage: MissionStageKey }) {
  const currentIndex = Math.max(
    0,
    stages.findIndex((stage) => stage.key === currentStage),
  );

  return (
    <div className="mission-stage-progress">
      {stages.map((stage, index) => {
        const state = index < currentIndex ? 'complete' : index === currentIndex ? 'active' : 'pending';
        return (
          <div className={`mission-stage-node mission-stage-node-${state}`} key={stage.key}>
            <div className="mission-stage-connector" />
            <div className="mission-stage-icon">
              <Icon name={stage.icon} />
            </div>
            <strong>{stage.label}</strong>
            <span>{state === 'active' ? 'Aktif' : state === 'complete' ? 'Tamamlandı' : 'Beklemede'}</span>
          </div>
        );
      })}
    </div>
  );
}
