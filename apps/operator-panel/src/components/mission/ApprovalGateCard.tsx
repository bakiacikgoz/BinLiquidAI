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
  onResolveDisabled,
}: {
  hasApproval: boolean;
  disabled: boolean;
  disabledReason: string;
  approvalLabel: string;
  onApprove: () => void;
  onEdit: () => void;
  onReject: () => void;
  onResolveDisabled?: () => void;
}) {
  const unavailableReason = hasApproval ? disabledReason : 'Bu çalıştırma için bekleyen operatör onayı bulunmuyor.';
  const mutationDisabledReason = disabled ? disabledReason : unavailableReason;
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
      {disabled && hasApproval ? (
        <div className="approval-disabled-helper">
          <p className="approval-disabled-reason">{disabledReason}</p>
          {onResolveDisabled ? (
            <button type="button" onClick={onResolveDisabled}>
              Operator ID ayarla
            </button>
          ) : null}
        </div>
      ) : null}
      <div className="approval-actions">
        <Button
          icon={<Icon name="check" />}
          variant="primary"
          disabled={!hasApproval || disabled}
          title={!hasApproval || disabled ? mutationDisabledReason : undefined}
          data-disabled-reason={!hasApproval || disabled ? mutationDisabledReason : undefined}
          onClick={onApprove}
        >
          Onayla ve Devam Et
        </Button>
        <div className="approval-secondary-actions">
          <Button
            icon={<Icon name="edit" />}
            variant="secondary"
            disabled={!hasApproval}
            title={!hasApproval ? unavailableReason : undefined}
            data-disabled-reason={!hasApproval ? unavailableReason : undefined}
            onClick={onEdit}
          >
            Düzenle
          </Button>
          <Button
            icon={<Icon name="reject" />}
            variant="danger"
            disabled={!hasApproval || disabled}
            title={!hasApproval || disabled ? mutationDisabledReason : undefined}
            data-disabled-reason={!hasApproval || disabled ? mutationDisabledReason : undefined}
            onClick={onReject}
          >
            Reddet
          </Button>
        </div>
      </div>
    </div>
  );
}
