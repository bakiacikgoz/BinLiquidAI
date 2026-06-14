import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MemorySemanticIndexView } from './MemorySemanticIndexView';

describe('MemorySemanticIndexView', () => {
  it('renders semantic index posture without raw payloads', () => {
    render(
      <MemorySemanticIndexView
        snapshot={{
          status: 'ready',
          enabled: true,
          runtimeInjectionEnabled: false,
          defaultBackend: 'in_memory_fixture',
          embeddingProfile: 'deterministic-fixture-v1',
          workspaceShardCount: 1,
          recordCount: 2,
          lastEvaluationStatus: 'pass',
          experimentalBackends: { turbovec: 'disabled' },
          backendStatus: { in_memory_fixture: 'ready' },
          rawPersistence: false,
          reasonCodes: [],
        }}
      />,
    );

    expect(screen.getByTestId('memory-semantic-status')).toHaveTextContent('ready');
    expect(screen.getByTestId('memory-semantic-backend')).toHaveTextContent('in_memory_fixture');
    expect(screen.getByText('blocked')).toBeInTheDocument();
  });
});
