import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderOperatorPanel } from '../../test/render';
import { ExportArtifactsModal } from './ExportArtifactsModal';

describe('ExportArtifactsModal interactions', () => {
  it('validates the export path and submits the selected target', async () => {
    const onClose = vi.fn();
    const onSubmit = vi.fn();
    const { user } = renderOperatorPanel(
      <ExportArtifactsModal
        open
        runId="run_1"
        initialPath="./exports/run_1"
        locale="tr"
        onClose={onClose}
        onSubmit={onSubmit}
      />,
    );

    const pathInput = screen.getByLabelText('Dışa aktarım yolu');
    await user.clear(pathInput);
    expect(screen.getByRole('button', { name: 'Dışa aktar' })).toBeDisabled();

    await user.type(pathInput, './exports/custom-run');
    await user.click(screen.getByRole('button', { name: 'Dışa aktar' }));

    expect(onSubmit).toHaveBeenCalledWith('./exports/custom-run');
  });

  it('closes the export modal from the header control', async () => {
    const onClose = vi.fn();
    const { user } = renderOperatorPanel(
      <ExportArtifactsModal
        open
        runId="run_1"
        initialPath="./exports/run_1"
        locale="tr"
        onClose={onClose}
        onSubmit={() => undefined}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Dışa aktarım modalını kapat' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
