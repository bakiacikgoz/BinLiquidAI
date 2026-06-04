import { describe, expect, it } from 'vitest';
import {
  boundaryBucket,
  computeVerdict,
  deadCodeBucket,
  duplicationBucket,
  healthBucket,
  highConfidenceSecretFindings,
} from './fallow-policy';

describe('fallow policy helpers', () => {
  it('treats unresolved imports and boundary violations as blocking errors', () => {
    const dead = deadCodeBucket({
      total_issues: 3,
      summary: {
        total_issues: 3,
        unused_files: 1,
        unresolved_imports: 1,
        unlisted_dependencies: 1,
      },
      unused_files: [{ path: 'src/unused.ts' }],
    });
    const boundaries = boundaryBucket({
      summary: { boundary_violations: 1 },
      boundary_violations: [{ from: 'src/components/primitives/Button.tsx' }],
    });

    const verdict = computeVerdict({
      dead_code: dead,
      duplication: duplicationBucket({ stats: { clone_groups: 0 }, clone_groups: [] }),
      health: healthBucket({ findings: [] }),
      boundaries,
      secret_scan: { status: 'pass', findings: [] },
    });

    expect(verdict.verdict).toBe('fail');
    expect(verdict.blockingReasons).toContain('FALLOW_AUDIT_FAILED');
    expect(verdict.blockingReasons).toContain('FALLOW_BOUNDARY_VIOLATION');
  });

  it('keeps existing unused/duplication/health findings in warn mode', () => {
    const verdict = computeVerdict({
      dead_code: deadCodeBucket({
        total_issues: 2,
        summary: { total_issues: 2, unused_files: 1, unused_exports: 1 },
      }),
      duplication: duplicationBucket({
        stats: { clone_groups: 1 },
        clone_groups: [{ instances: [{ file: 'src/App.tsx' }] }],
      }),
      health: healthBucket({ findings: [{ path: 'src/App.tsx', severity: 'critical' }] }),
      boundaries: boundaryBucket({ summary: { boundary_violations: 0 } }),
      secret_scan: { status: 'pass', findings: [] },
    });

    expect(verdict.verdict).toBe('warn');
    expect(verdict.blockingReasons).toEqual([]);
    expect(verdict.warnings.join(',')).toContain('dead_code');
    expect(verdict.warnings.join(',')).toContain('duplication');
    expect(verdict.warnings.join(',')).toContain('health');
  });

  it('detects high-confidence secret tokens without flagging ordinary words', () => {
    expect(highConfidenceSecretFindings('secret redaction policy')).toEqual([]);
    expect(highConfidenceSecretFindings('token ghp_123456789012345678901234567890')).toContain(
      'github-token',
    );
  });
});
