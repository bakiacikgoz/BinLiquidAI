import { lazy, Suspense, useState } from 'react';

import type {
  ArtifactContent,
  ArtifactAssetDescriptor,
  ArtifactDescriptor,
  ArtifactFormSubmissionRequest,
  ArtifactFormSubmissionResult,
  ArtifactLicenseCapability,
  ArtifactRevision,
} from '../artifactContracts';
import type { ArtifactSaveState } from '../workspaceController';
import { isArtifactCodeEditorEnabled, isArtifactFlowEditorEnabled, isArtifactFormEditorEnabled, isArtifactSlidesEditorEnabled } from '../artifactFeatureFlags';
import type { ArtifactContextSelection } from '../selectionContext';
import { FormSessionRuntime } from './form/formSessionRuntime';
import { ArtifactLicenseBlocked } from '../ui/ArtifactLicenseBlocked';

export type ArtifactSelection = ArtifactContextSelection;
export type ArtifactExportFormat = 'json' | 'markdown' | 'html' | 'txt' | 'source' | 'svg' | 'png' | 'csv' | 'xlsx' | 'pptx';

export interface ArtifactEditorProps {
  artifact: ArtifactDescriptor;
  revision: ArtifactRevision;
  content: ArtifactContent;
  mode: 'view' | 'edit' | 'suggest';
  saveState: ArtifactSaveState;
  onChange(next: ArtifactContent, selection?: ArtifactSelection): void;
  onSelectionChange(selection: ArtifactSelection | null): void;
  onRequestExport(format: ArtifactExportFormat): void;
  onImportAsset?(): Promise<ArtifactAssetDescriptor | null>;
}

export interface ArtifactEditorHostProps extends ArtifactEditorProps {
  formRuntime?: FormSessionRuntime;
  onSubmitForm?(request: ArtifactFormSubmissionRequest): Promise<ArtifactFormSubmissionResult>;
  formEnabled?: boolean;
  codeEnabled?: boolean;
  flowEnabled?: boolean;
  slidesEnabled?: boolean;
  licenseCapability?: ArtifactLicenseCapability;
  locale?: 'en' | 'tr';
}

const DocumentArtifactEditor = lazy(() =>
  import('./document/DocumentArtifactEditor').then((module) => ({
    default: module.DocumentArtifactEditor,
  })),
);

const FormArtifactEditor = lazy(() =>
  import('./form/FormArtifactEditor').then((module) => ({
    default: module.FormArtifactEditor,
  })),
);

const CodeArtifactEditor = lazy(() =>
  import('./code/CodeArtifactEditor').then((module) => ({
    default: module.CodeArtifactEditor,
  })),
);

const FlowArtifactEditor = lazy(() =>
  import('./flow/FlowArtifactEditor').then((module) => ({
    default: module.FlowArtifactEditor,
  })),
);

const SlidesArtifactEditor = lazy(() =>
  import('./slides/SlidesArtifactEditor').then((module) => ({
    default: module.SlidesArtifactEditor,
  })),
);

export function ArtifactEditorHost(props: ArtifactEditorHostProps) {
  const [ownedFormRuntime] = useState(() => new FormSessionRuntime());
  if (props.artifact.kind === 'form') {
    const enabled = props.formEnabled
      ?? isArtifactFormEditorEnabled(import.meta.env.VITE_ARTIFACT_FORM_EDITOR);
    if (!enabled) {
      return <div className="artifact-editor-placeholder" role="status">The form editor is disabled by policy.</div>;
    }
    return (
      <Suspense fallback={<div className="artifact-editor-loading" role="status">Loading form editor…</div>}>
        <FormArtifactEditor
          artifact={props.artifact}
          revision={props.revision}
          content={props.content}
          mode={props.mode === 'view' ? 'readonly' : 'edit'}
          runtime={props.formRuntime ?? ownedFormRuntime}
          locale={props.locale}
          onSubmit={props.onSubmitForm ? (response, idempotencyKey) => props.onSubmitForm?.({
            artifactId: props.artifact.artifactId,
            schemaRevisionId: props.revision.revisionId,
            response,
            persistencePolicy: 'none',
            idempotencyKey,
          }) as Promise<ArtifactFormSubmissionResult> : undefined}
        />
      </Suspense>
    );
  }
  if (props.artifact.kind === 'code') {
    const enabled = props.codeEnabled
      ?? isArtifactCodeEditorEnabled(import.meta.env.VITE_ARTIFACT_CODE_EDITOR);
    if (!enabled) {
      return <div className="artifact-editor-placeholder" role="status">The code editor is disabled by policy.</div>;
    }
    return (
      <Suspense fallback={<div className="artifact-editor-loading" role="status">Loading code editor…</div>}>
        <CodeArtifactEditor {...props} />
      </Suspense>
    );
  }
  if (props.artifact.kind === 'flow') {
    const enabled = props.flowEnabled
      ?? isArtifactFlowEditorEnabled(import.meta.env.VITE_ARTIFACT_FLOW_EDITOR);
    if (!enabled) {
      return <div className="artifact-editor-placeholder" role="status">The flow editor is disabled by policy.</div>;
    }
    return (
      <Suspense fallback={<div className="artifact-editor-loading" role="status">Loading flow editor…</div>}>
        <FlowArtifactEditor {...props} />
      </Suspense>
    );
  }
  if (props.artifact.kind === 'spreadsheet' || props.artifact.kind === 'canvas') {
    const capability = props.licenseCapability ?? {
      contractVersion: 'artifact-license-capability/v1' as const,
      kind: props.artifact.kind,
      enabled: false,
      reasonCode: 'ARTIFACT_LICENSE_EVIDENCE_MISSING',
    };
    return <ArtifactLicenseBlocked
      artifact={props.artifact}
      content={props.content}
      capability={capability}
      onExportJson={props.artifact.kind === 'canvas' ? () => props.onRequestExport('json') : undefined}
    />;
  }
  if (props.artifact.kind === 'slides') {
    const enabled = props.slidesEnabled
      ?? isArtifactSlidesEditorEnabled(import.meta.env.VITE_ARTIFACT_SLIDES_EDITOR);
    if (!enabled) {
      return <div className="artifact-editor-placeholder" role="status">The slides editor is disabled by policy.</div>;
    }
    return (
      <Suspense fallback={<div className="artifact-editor-loading" role="status">Loading slides editor…</div>}>
        <SlidesArtifactEditor key={props.artifact.artifactId} {...props} />
      </Suspense>
    );
  }
  if (props.artifact.kind !== 'document') {
    return (
      <div className="artifact-editor-placeholder" role="status">
        The {props.artifact.kind} editor will load in its governed implementation phase.
      </div>
    );
  }
  return (
    <Suspense fallback={<div className="artifact-editor-loading" role="status">Loading document editor…</div>}>
      <DocumentArtifactEditor {...props} />
    </Suspense>
  );
}
