import { lazy, Suspense } from 'react';

import type { ArtifactContent, ArtifactDescriptor, ArtifactRevision } from '../artifactContracts';
import type { ArtifactSaveState } from '../workspaceController';
import type { DocumentArtifactSelection } from './document/documentAdapter';

export type ArtifactSelection = DocumentArtifactSelection;
export type ArtifactExportFormat = 'json' | 'markdown' | 'html' | 'txt';

export interface ArtifactEditorProps {
  artifact: ArtifactDescriptor;
  revision: ArtifactRevision;
  content: ArtifactContent;
  mode: 'view' | 'edit' | 'suggest';
  saveState: ArtifactSaveState;
  onChange(next: ArtifactContent, selection?: ArtifactSelection): void;
  onSelectionChange(selection: ArtifactSelection | null): void;
  onRequestExport(format: ArtifactExportFormat): void;
}

const DocumentArtifactEditor = lazy(() =>
  import('./document/DocumentArtifactEditor').then((module) => ({
    default: module.DocumentArtifactEditor,
  })),
);

export function ArtifactEditorHost(props: ArtifactEditorProps) {
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
