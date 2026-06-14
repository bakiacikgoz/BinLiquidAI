import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MemoryRuntimePolicyView } from './MemoryRuntimePolicyView';

describe('MemoryRuntimePolicyView', () => {
  it('renders policy enforcement posture without raw payloads', () => {
    render(
      <MemoryRuntimePolicyView
        snapshot={{
          contractVersion: 'memory-policy-enforcement-snapshot/v1',
          generatedAtUtc: '2026-06-14T00:00:00Z',
          status: 'pass',
          enabled: true,
          semanticRuntimeMode: 'enforced',
          readEventCount: 3,
          writeEventCount: 2,
          deniedCount: 1,
          approvalRequiredCount: 1,
          degradedCount: 0,
          rawLeakCount: 0,
          latestEvidenceRefs: ['artifacts/memory-runtime-policy/events/event.json'],
          reasonCodes: ['MEMORY_RUNTIME_POLICY_SHADOW'],
          rawContentIncluded: false,
        }}
      />,
    );

    expect(screen.getByTestId('memory-policy-enforcement')).toHaveTextContent('enforced');
    expect(screen.getByTestId('memory-policy-enforcement')).toHaveTextContent('Raw leaks');
    expect(screen.queryByText('raw query')).not.toBeInTheDocument();
  });
});
