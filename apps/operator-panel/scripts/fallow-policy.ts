import fs from 'node:fs';
import path from 'node:path';

export type FallowVerdict = 'pass' | 'warn' | 'fail' | 'conditional';

export interface FindingBucket {
  total: number;
  new?: number;
  suppressed?: number;
  stale_suppressions?: number;
  errors: number;
  warnings: number;
  top_files?: Array<{ path: string; count: number }>;
  notes?: string[];
}

export interface FallowCommandArtifact {
  command: string;
  exit_code: number;
  stdout_path: string;
  stderr_path: string;
  parsed_json_path?: string;
  started_at: string;
  finished_at: string;
}

export interface CodeIntelligenceSummary {
  version: 'control-plane.code-intelligence/v1';
  generated_at: string;
  tool: 'fallow';
  tool_version: string;
  scope: 'apps/operator-panel';
  mode: 'repo_clean' | 'audit' | 'ci';
  telemetry_disabled: boolean;
  dead_code: FindingBucket;
  duplication: FindingBucket;
  health: FindingBucket;
  boundaries: FindingBucket;
  verdict: FallowVerdict;
  baseline_used: boolean;
  commands: FallowCommandArtifact[];
  artifacts: string[];
  rollout_gate?: FallowRolloutGate;
  baseline_warnings?: string[];
  secret_scan: {
    status: 'pass' | 'fail';
    findings: string[];
  };
  blocking_reasons: string[];
  warnings: string[];
}

export interface FallowRolloutGate {
  gate: 'new-only';
  status: 'pass' | 'warn' | 'fail';
  base_ref: string;
  head_sha: string;
  changed_files_count: number;
  introduced: {
    dead_code: number;
    duplication: number;
    health: number;
  };
  inherited: {
    dead_code: number;
    duplication: number;
    health: number;
  };
  warnings: string[];
  blocking_reasons: string[];
}

type JsonRecord = Record<string, unknown>;

export const ERROR_DEAD_CODE_KEYS = [
  'unresolved_imports',
  'unlisted_dependencies',
  'duplicate_exports',
  'boundary_violations',
  'unresolved_catalog_references',
  'misconfigured_dependency_overrides',
] as const;

export function asRecord(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as JsonRecord)
    : {};
}

export function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

export function asNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

export function countByPath(items: unknown[], pathKey = 'path'): Array<{ path: string; count: number }> {
  const counts = new Map<string, number>();
  for (const item of items) {
    const record = asRecord(item);
    const itemPath = record[pathKey];
    if (typeof itemPath === 'string') {
      counts.set(itemPath, (counts.get(itemPath) ?? 0) + 1);
    }
  }
  return Array.from(counts.entries())
    .map(([itemPath, count]) => ({ path: itemPath, count }))
    .sort((a, b) => b.count - a.count || a.path.localeCompare(b.path))
    .slice(0, 20);
}

export function deadCodeBucket(payload: unknown): FindingBucket {
  const record = asRecord(payload);
  const summary = asRecord(record.summary);
  const errors = ERROR_DEAD_CODE_KEYS.reduce((total, key) => total + asNumber(summary[key]), 0);
  const total = asNumber(record.total_issues) || asNumber(summary.total_issues);
  const files = [
    ...asArray(record.unused_files),
    ...asArray(record.unused_exports),
    ...asArray(record.unused_types),
    ...asArray(record.unused_dependencies),
    ...asArray(record.unused_dev_dependencies),
    ...asArray(record.circular_dependencies),
  ];
  return {
    total,
    errors,
    warnings: Math.max(0, total - errors),
    stale_suppressions: asNumber(summary.stale_suppressions),
    top_files: countByPath(files),
    notes: [
      `unused_files=${asNumber(summary.unused_files)}`,
      `unused_exports=${asNumber(summary.unused_exports)}`,
      `unused_types=${asNumber(summary.unused_types)}`,
      `unresolved_imports=${asNumber(summary.unresolved_imports)}`,
      `unlisted_dependencies=${asNumber(summary.unlisted_dependencies)}`,
    ],
  };
}

export function duplicationBucket(payload: unknown): FindingBucket {
  const record = asRecord(payload);
  const stats = asRecord(record.stats);
  const cloneGroups = asArray(record.clone_groups);
  const total = asNumber(stats.clone_groups) || cloneGroups.length;
  const files: Array<{ path: string; count: number }> = [];
  const counts = new Map<string, number>();
  for (const group of cloneGroups) {
    for (const instance of asArray(asRecord(group).instances)) {
      const file = asRecord(instance).file;
      if (typeof file === 'string') {
        counts.set(file, (counts.get(file) ?? 0) + 1);
      }
    }
  }
  for (const [itemPath, count] of counts.entries()) {
    files.push({ path: itemPath, count });
  }
  return {
    total,
    errors: 0,
    warnings: total,
    top_files: files.sort((a, b) => b.count - a.count || a.path.localeCompare(b.path)).slice(0, 20),
    notes: [
      `duplicated_lines=${asNumber(stats.duplicated_lines)}`,
      `duplication_percentage=${asNumber(stats.duplication_percentage).toFixed(2)}`,
    ],
  };
}

export function healthBucket(payload: unknown): FindingBucket {
  const record = asRecord(payload);
  const findings = asArray(record.findings);
  const errors = findings.filter((item) => asRecord(item).severity === 'critical').length;
  return {
    total: findings.length,
    errors: 0,
    warnings: findings.length,
    top_files: countByPath(findings),
    notes: [`critical=${errors}`, `targets=${asArray(record.targets).length}`],
  };
}

export function boundaryBucket(payload: unknown): FindingBucket {
  const record = asRecord(payload);
  const summary = asRecord(record.summary);
  const violations = asArray(record.boundary_violations);
  const total = asNumber(summary.boundary_violations) || violations.length;
  return {
    total,
    errors: total,
    warnings: 0,
    top_files: countByPath(violations, 'from'),
  };
}

export function computeVerdict(summary: Pick<CodeIntelligenceSummary, 'dead_code' | 'duplication' | 'health' | 'boundaries' | 'secret_scan' | 'rollout_gate'>): {
  verdict: FallowVerdict;
  blockingReasons: string[];
  warnings: string[];
} {
  const blockingReasons = baseBlockingReasons(summary);
  if (summary.rollout_gate) {
    return verdictFrom(
      [...blockingReasons, ...summary.rollout_gate.blocking_reasons],
      summary.rollout_gate.warnings,
    );
  }
  return verdictFrom(blockingReasons, bucketWarnings(summary));
}

function baseBlockingReasons(
  summary: Pick<CodeIntelligenceSummary, 'dead_code' | 'boundaries' | 'secret_scan'>,
): string[] {
  return [
    summary.dead_code.errors > 0 ? 'FALLOW_AUDIT_FAILED' : null,
    summary.boundaries.errors > 0 ? 'FALLOW_BOUNDARY_VIOLATION' : null,
    summary.secret_scan.status !== 'pass' ? 'FALLOW_ARTIFACT_SECRET_SCAN_FAILED' : null,
  ].filter((item): item is string => item !== null);
}

function bucketWarnings(
  summary: Pick<CodeIntelligenceSummary, 'dead_code' | 'duplication' | 'health' | 'boundaries'>,
): string[] {
  return Object.entries({
    dead_code: summary.dead_code,
    duplication: summary.duplication,
    health: summary.health,
    boundaries: summary.boundaries,
  })
    .filter(([, bucket]) => bucket.total > 0 && bucket.errors === 0)
    .map(([label, bucket]) => `${label}:${bucket.total}`);
}

function verdictFrom(blockingReasons: string[], warnings: string[]): {
  verdict: FallowVerdict;
  blockingReasons: string[];
  warnings: string[];
} {
  return {
    verdict: blockingReasons.length > 0 ? 'fail' : warnings.length > 0 ? 'warn' : 'pass',
    blockingReasons,
    warnings,
  };
}

export function findRepoRoot(start: string): string {
  let current = start;
  while (current !== path.dirname(current)) {
    if (fs.existsSync(path.join(current, 'pnpm-workspace.yaml')) || fs.existsSync(path.join(current, '.git'))) {
      return current;
    }
    current = path.dirname(current);
  }
  return start;
}

export function readJson(filePath: string): JsonRecord {
  return JSON.parse(fs.readFileSync(filePath, 'utf8')) as JsonRecord;
}

export function relativeToRepo(repoRoot: string, filePath: string): string {
  return path.relative(repoRoot, filePath).split(path.sep).join('/');
}

export function highConfidenceSecretFindings(text: string): string[] {
  const patterns: Array<[string, RegExp]> = [
    ['private-key', /-----BEGIN [A-Z ]*PRIVATE KEY-----/],
    ['openai-key', /\bsk-[A-Za-z0-9_-]{20,}\b/],
    ['github-token', /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/],
    ['aws-access-key', /\bAKIA[0-9A-Z]{16}\b/],
  ];
  return patterns
    .filter(([, pattern]) => pattern.test(text))
    .map(([label]) => label);
}

export function writeJson(filePath: string, payload: unknown): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
}
