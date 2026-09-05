import { Icon } from '../primitives/Icon';

export function ComputerUseBlockerChecklist({
  blocked,
  reason,
  blockers,
  onOpenSettings,
}: {
  blocked: boolean;
  reason: string;
  blockers: string[];
  onOpenSettings: () => void;
}) {
  if (!blocked) {
    return null;
  }

  const visibleBlockers = blockers.length > 0 ? blockers : [reason || 'Computer-use runtime is not qualified yet.'];

  return (
    <div className="computer-use-blocker-checklist" role="note" aria-label="Computer-use blockers">
      <div>
        <Icon name="alert" />
        <strong>Computer-use oturumu şu an başlatılamaz</strong>
      </div>
      <ul>
        {visibleBlockers.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <button type="button" onClick={onOpenSettings}>
        Ayarlara git
      </button>
    </div>
  );
}
