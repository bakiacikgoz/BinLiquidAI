import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TargetClosureActionsView } from './TargetClosureActionsView';

describe('TargetClosureActionsView', () => {
  it('shows missing target commands without broad ready claims', () => {
    render(
      <TargetClosureActionsView
        actions={[
          {
            target: 'darwin-arm64',
            status: 'not_evidenced',
            recommendedPath: 'manual_local',
            commands: ['uv run binliquid local-product evidence collect --target current'],
            runbook: 'docs/MACOS_LOCAL_EVIDENCE_RUNBOOK.md',
          },
        ]}
      />,
    );

    expect(screen.getByText('Missing Target Actions')).toBeInTheDocument();
    expect(screen.getByText('darwin-arm64')).toBeInTheDocument();
    expect(screen.queryByText(/all platforms ready/i)).not.toBeInTheDocument();
  });
});

