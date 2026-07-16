import { useEffect } from 'react';

import type { ArtifactFormSubmissionRequest, ArtifactFormSubmissionResult } from './artifactContracts';
import { ArtifactEditorHost } from './editors/ArtifactEditorHost';
import type { FormSessionRuntime } from './editors/form/formSessionRuntime';
import type { ArtifactWorkspaceTab } from './workspaceController';

export function AssistantInlineFormPart({
  artifactId,
  tab,
  loading,
  locale,
  formRuntime,
  onLoad,
  onExpand,
  onSubmit,
}: {
  artifactId: string;
  tab: ArtifactWorkspaceTab | null;
  loading: boolean;
  locale: 'en' | 'tr';
  formRuntime: FormSessionRuntime;
  onLoad: (artifactId: string) => void;
  onExpand: (artifactId: string) => void;
  onSubmit: (request: ArtifactFormSubmissionRequest) => Promise<ArtifactFormSubmissionResult>;
}) {
  useEffect(() => {
    if (!tab && !loading) onLoad(artifactId);
  }, [artifactId, loading, onLoad, tab]);

  if (!tab) {
    return (
      <div className="assistant-inline-form" role="status">
        {locale === 'tr' ? 'GÃ¼venli form yÃ¼kleniyorâ€¦' : 'Loading governed formâ€¦'}
      </div>
    );
  }
  if (tab.artifact.kind !== 'form') {
    return <div className="assistant-inline-form" role="alert">The referenced artifact is not a form.</div>;
  }
  return (
    <section className="assistant-inline-form" aria-label={`Inline form: ${tab.artifact.title}`}>
      <ArtifactEditorHost
        artifact={tab.artifact}
        revision={tab.revision}
        content={tab.draftContent}
        mode={tab.artifact.status === 'archived' ? 'view' : 'edit'}
        saveState={tab.saveState}
        onChange={() => undefined}
        onSelectionChange={() => undefined}
        onRequestExport={() => undefined}
        formRuntime={formRuntime}
        onSubmitForm={onSubmit}
        locale={locale}
      />
      <button type="button" onClick={() => onExpand(artifactId)}>
        {locale === 'tr' ? 'Ã‡alÄ±ÅŸma alanÄ±nda geniÅŸlet' : 'Expand in Workbench'}
      </button>
    </section>
  );
}
