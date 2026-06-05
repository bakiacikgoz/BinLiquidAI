import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type {
  CodeIntelligenceSummary,
  DesignPartnerBetaStatus,
  PilotOperationsStatus,
} from '../../control-plane/types';
import { renderOperatorPanel } from '../../test/render';
import { DesignPartnerBetaReadinessCard } from './DesignPartnerBetaReadinessCard';

const generatedAtUtc = '2026-06-04T20:00:00Z';

const codeIntelligence: CodeIntelligenceSummary = {
  schemaVersion: 'control-plane.code-intelligence-summary/v1',
  generatedAtUtc,
  status: 'ready',
  verdict: 'pass',
  tool: 'fallow',
  toolVersion: '2.88.3',
  artifactRoot: 'artifacts/code-intelligence/fallow',
  telemetryDisabled: true,
  boundaryViolations: 0,
  secretScanStatus: 'pass',
  buckets: [
    {
      bucketId: 'dead-code',
      label: 'Dead code',
      status: 'warn',
      count: 22,
      errors: 0,
      warnings: 22,
      path: 'artifacts/code-intelligence/fallow/dead-code.json',
      detail: 'baseline retained',
    },
  ],
  blockers: [],
  warnings: [],
};

const pilotOperations: PilotOperationsStatus = {
  schemaVersion: 'control-plane.pilot-operations/v1',
  generatedAtUtc,
  status: 'ready',
  headline: 'Pilot operations are ready.',
  artifactRoot: 'artifacts/pilot-ops',
  checklist: [],
  timeline: [],
  acceptanceMetrics: {},
  feedbackBundlePath: 'artifacts/pilot-ops/pilot_feedback_bundle.json',
  nextActions: [
    {
      label: 'Review design partner feedback bundle',
      severity: 'info',
      target: 'Pilot Ops',
    },
  ],
  blockers: [],
  warnings: [],
};

const designPartnerBeta: DesignPartnerBetaStatus = {
  schemaVersion: 'control-plane.design-partner-beta/v1',
  generatedAtUtc,
  status: 'ready',
  headline: 'Design Partner Beta Operations Candidate is ready.',
  artifactRoot: 'artifacts/design-partner-beta',
  codeIntelligence,
  pilotOperations,
  checks: [
    {
      itemId: 'external-agent-v1-1',
      label: 'External Agent Gateway v1.1',
      status: 'ready',
      detail: 'status=pass',
      path: 'artifacts/external-agent-v1-1/results.json',
      blocking: false,
    },
    {
      itemId: 'ci-node24-inventory',
      label: 'CI Node action inventory',
      status: 'ready',
      detail: 'status=pass',
      path: 'artifacts/ci/node-action-inventory.json',
      blocking: false,
    },
    {
      itemId: 'safety-claims',
      label: 'Safety claims remain blocked',
      status: 'ready',
      detail: 'computer-use live and public desktop installer remain blocked',
      path: null,
      blocking: false,
    },
  ],
  blockers: [],
  warnings: [],
};

describe('DesignPartnerBetaReadinessCard', () => {
  it('renders partner beta readiness without raw JSON', () => {
    renderOperatorPanel(
      <DesignPartnerBetaReadinessCard
        codeIntelligence={codeIntelligence}
        pilotOperations={pilotOperations}
        designPartnerBeta={designPartnerBeta}
      />,
    );

    expect(screen.getByRole('heading', { name: 'Beta Operations' })).toBeInTheDocument();
    expect(screen.getByText('ready / pass')).toBeInTheDocument();
    expect(screen.getAllByText('ready (status=pass)')).toHaveLength(2);
    expect(
      screen.getByText('ready (computer-use live and public desktop installer remain blocked)'),
    ).toBeInTheDocument();
    expect(screen.getByText('info: Review design partner feedback bundle')).toBeInTheDocument();
    expect(screen.getByText('Dead code: 22')).toBeInTheDocument();
    expect(screen.queryByText('schemaVersion')).not.toBeInTheDocument();
  });
});
