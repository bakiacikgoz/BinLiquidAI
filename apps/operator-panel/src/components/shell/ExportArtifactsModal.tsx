import { useEffect, useState } from 'react';

import type { UiLocale } from '../../i18n';
import { Button } from '../primitives/Button';

const copy = {
  en: {
    pathRequired: 'Export path is required.',
    invalidPath: 'Export path contains an invalid character.',
    alreadyRunning: 'Export is already running.',
    noRunSelected: 'No run is selected.',
    runExport: 'Run export',
    title: 'Export logs',
    close: 'Close export modal',
    noRunBody: 'Select a run first.',
    pathLabel: 'Export path',
    cancel: 'Cancel',
    exporting: 'Exporting',
    export: 'Export',
  },
  tr: {
    pathRequired: 'Dışa aktarım yolu gerekli.',
    invalidPath: 'Dışa aktarım yolu geçersiz bir karakter içeriyor.',
    alreadyRunning: 'Dışa aktarım zaten çalışıyor.',
    noRunSelected: 'Seçili run yok.',
    runExport: 'Run dışa aktarımı',
    title: 'Logları dışa aktar',
    close: 'Dışa aktarım modalını kapat',
    noRunBody: 'Önce bir çalıştırma seçin.',
    pathLabel: 'Dışa aktarım yolu',
    cancel: 'Vazgeç',
    exporting: 'Aktarılıyor',
    export: 'Dışa aktar',
  },
} satisfies Record<UiLocale, Record<string, string>>;

function validateExportPath(value: string, locale: UiLocale): string {
  const text = copy[locale];
  const trimmed = value.trim();
  if (!trimmed) {
    return text.pathRequired;
  }
  if (trimmed.includes('\0')) {
    return text.invalidPath;
  }
  return '';
}

export function ExportArtifactsModal({
  open,
  runId,
  initialPath,
  submitting = false,
  locale = 'en',
  onClose,
  onSubmit,
}: {
  open: boolean;
  runId: string;
  initialPath: string;
  submitting?: boolean;
  locale?: UiLocale;
  onClose: () => void;
  onSubmit: (path: string) => void;
}) {
  const text = copy[locale];
  const [path, setPath] = useState(initialPath);

  useEffect(() => {
    if (open) {
      setPath(initialPath);
    }
  }, [initialPath, open]);

  if (!open) {
    return null;
  }

  const validation = validateExportPath(path, locale);
  const submitDisabledReason =
    validation || (submitting ? text.alreadyRunning : !runId ? text.noRunSelected : undefined);
  const onCancelExport = () => {
    onClose();
  };
  const onSubmitExport = () => {
    onSubmit(path.trim());
  };

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="export-modal" role="dialog" aria-modal="true" aria-labelledby="export-modal-title">
        <div className="export-modal-head">
          <div>
            <span>{text.runExport}</span>
            <h2 id="export-modal-title">{text.title}</h2>
          </div>
          <button type="button" aria-label={text.close} onClick={onCancelExport}>
            ×
          </button>
        </div>
        <p className="export-modal-copy">
          {runId
            ? locale === 'tr'
              ? `${runId} için artifact ve log paketi hedef klasöre yazılacak.`
              : `Artifact and log package for ${runId} will be written to the target folder.`
            : text.noRunBody}
        </p>
        <label className="field">
          <span>{text.pathLabel}</span>
          <input
            autoFocus
            value={path}
            onChange={(event) => setPath(event.target.value)}
            placeholder="./exports/run-id"
            aria-invalid={Boolean(validation)}
            aria-describedby={validation ? 'export-path-error' : undefined}
          />
        </label>
        {validation ? (
          <p className="export-modal-error" id="export-path-error">
            {validation}
          </p>
        ) : null}
        <div className="export-modal-actions">
          <Button
            type="button"
            variant="ghost"
            onClick={onCancelExport}
            disabled={submitting}
            title={submitting ? text.alreadyRunning : text.close}
            data-disabled-reason={submitting ? text.alreadyRunning : undefined}
          >
            {text.cancel}
          </Button>
          <Button
            type="button"
            variant="primary"
            disabled={Boolean(submitDisabledReason)}
            title={submitDisabledReason}
            data-disabled-reason={submitDisabledReason}
            onClick={onSubmitExport}
          >
            {submitting ? text.exporting : text.export}
          </Button>
        </div>
      </section>
    </div>
  );
}
