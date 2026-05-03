import { Button } from '../primitives/Button';
import { Icon } from '../primitives/Icon';

export function ApprovalGateCard({
  hasApproval,
  disabled,
  disabledReason,
  approvalLabel,
  onApprove,
  onEdit,
  onReject,
}: {
  hasApproval: boolean;
  disabled: boolean;
  disabledReason: string;
  approvalLabel: string;
  onApprove: () => void;
  onEdit: () => void;
  onReject: () => void;
}) {
  return (
    <div className="mc-card approval-gate-card">
      <span className="mc-kicker">ONAY KAPISI</span>
      <div className="approval-gate-head">
        <span className="approval-shield">
          <Icon name="shield" />
        </span>
        <div>
          <h3>{hasApproval ? 'Operatör onayı gerekiyor' : 'Onay beklenmiyor'}</h3>
          <p>
            {hasApproval
              ? 'Planlama tamamlandı. Bir sonraki aşamaya geçmek için onayınız bekleniyor.'
              : 'Bu çalıştırma için bekleyen operatör onayı bulunmuyor.'}
          </p>
        </div>
      </div>
      <div className="approval-requested-action">
        <span>İSTENEN EYLEM</span>
        <p>{approvalLabel || 'Plan gözden geçir ve çalıştırmaya izin ver.'}</p>
      </div>
      {disabled && hasApproval ? <p className="approval-disabled-reason">{disabledReason}</p> : null}
      <div className="approval-actions">
        <Button icon={<Icon name="check" />} variant="primary" disabled={!hasApproval || disabled} onClick={onApprove}>
          Onayla ve Devam Et
        </Button>
        <div className="approval-secondary-actions">
          <Button icon={<Icon name="edit" />} variant="secondary" disabled={!hasApproval} onClick={onEdit}>
            Düzenle
          </Button>
          <Button icon={<Icon name="reject" />} variant="danger" disabled={!hasApproval || disabled} onClick={onReject}>
            Reddet
          </Button>
        </div>
      </div>
    </div>
  );
}
