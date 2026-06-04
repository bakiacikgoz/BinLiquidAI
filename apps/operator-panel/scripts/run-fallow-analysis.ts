import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {
  boundaryBucket,
  computeVerdict,
  deadCodeBucket,
  duplicationBucket,
  findRepoRoot,
  healthBucket,
  highConfidenceSecretFindings,
  relativeToRepo,
  writeJson,
  type CodeIntelligenceSummary,
  type FallowCommandArtifact,
} from './fallow-policy.ts';

type FallowCommandName = 'dead-code' | 'dupes' | 'health' | 'audit' | 'boundary-violations' | 'fix-dry-run';

interface CommandSpec {
  name: FallowCommandName;
  args: string[];
  required: boolean;
}

interface CommandRun {
  artifact: FallowCommandArtifact;
  parsed: unknown | null;
  parse_error?: string;
}

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const APP_ROOT = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = findRepoRoot(APP_ROOT);
const DEFAULT_OUTPUT_ROOT = path.join(REPO_ROOT, 'artifacts', 'code-intelligence', 'fallow');

function argValue(name: string, fallback: string): string {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) {
    return fallback;
  }
  return process.argv[index + 1];
}

function runCommand(spec: CommandSpec, outputRoot: string): CommandRun {
  const startedAt = new Date().toISOString();
  const stdoutPath = path.join(outputRoot, `${spec.name}.stdout.json`);
  const stderrPath = path.join(outputRoot, `${spec.name}.stderr.txt`);
  const parsedJsonPath = path.join(outputRoot, `${spec.name}.json`);
  const result = spawnSync('fallow', spec.args, {
    cwd: APP_ROOT,
    env: {
      ...process.env,
      FALLOW_TELEMETRY_DISABLED: '1',
      DO_NOT_TRACK: '1',
    },
    encoding: 'utf8',
  });
  fs.mkdirSync(outputRoot, { recursive: true });
  fs.writeFileSync(stdoutPath, result.stdout ?? '', 'utf8');
  fs.writeFileSync(stderrPath, result.stderr ?? '', 'utf8');
  let parsed: unknown | null = null;
  let parseError: string | undefined;
  if ((result.stdout ?? '').trim()) {
    try {
      parsed = JSON.parse(result.stdout);
      writeJson(parsedJsonPath, parsed);
    } catch (error) {
      parseError = error instanceof Error ? error.message : String(error);
    }
  } else if (spec.required) {
    parseError = 'Fallow command produced no JSON stdout';
  }
  return {
    artifact: {
      command: spec.name,
      exit_code: result.status ?? 1,
      stdout_path: relativeToRepo(REPO_ROOT, stdoutPath),
      stderr_path: relativeToRepo(REPO_ROOT, stderrPath),
      parsed_json_path: parsed ? relativeToRepo(REPO_ROOT, parsedJsonPath) : undefined,
      started_at: startedAt,
      finished_at: new Date().toISOString(),
    },
    parsed,
    parse_error: parseError,
  };
}

function gitHasRef(ref: string): boolean {
  const result = spawnSync('git', ['rev-parse', '--verify', ref], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
  });
  return result.status === 0;
}

function auditBase(): string {
  const explicit = process.env.FALLOW_AUDIT_BASE;
  if (explicit) {
    return explicit;
  }
  if (gitHasRef('origin/main')) {
    return 'origin/main';
  }
  if (gitHasRef('HEAD~1')) {
    return 'HEAD~1';
  }
  return 'HEAD';
}

function commandSpecs(): CommandSpec[] {
  const base = auditBase();
  return [
    { name: 'dead-code', args: ['dead-code', '--format', 'json', '--quiet'], required: true },
    { name: 'dupes', args: ['dupes', '--format', 'json', '--quiet'], required: true },
    { name: 'health', args: ['health', '--format', 'json', '--quiet'], required: true },
    {
      name: 'audit',
      args: ['audit', '--format', 'json', '--quiet', '--changed-since', base],
      required: false,
    },
    {
      name: 'boundary-violations',
      args: ['dead-code', '--boundary-violations', '--format', 'json', '--quiet'],
      required: true,
    },
    {
      name: 'fix-dry-run',
      args: ['fix', '--dry-run', '--format', 'json', '--quiet'],
      required: false,
    },
  ];
}

function writeMarkdown(summary: CodeIntelligenceSummary, outputRoot: string): string {
  const lines = [
    '# Fallow Code Intelligence',
    '',
    `Generated: ${summary.generated_at}`,
    `Tool: ${summary.tool} ${summary.tool_version}`,
    `Scope: ${summary.scope}`,
    `Verdict: ${summary.verdict}`,
    `Telemetry disabled: ${summary.telemetry_disabled ? 'yes' : 'no'}`,
    '',
    '| Bucket | Total | Errors | Warnings | Notes |',
    '|---|---:|---:|---:|---|',
    `| Dead code | ${summary.dead_code.total} | ${summary.dead_code.errors} | ${summary.dead_code.warnings} | ${(summary.dead_code.notes ?? []).join(', ')} |`,
    `| Duplication | ${summary.duplication.total} | ${summary.duplication.errors} | ${summary.duplication.warnings} | ${(summary.duplication.notes ?? []).join(', ')} |`,
    `| Health | ${summary.health.total} | ${summary.health.errors} | ${summary.health.warnings} | ${(summary.health.notes ?? []).join(', ')} |`,
    `| Boundaries | ${summary.boundaries.total} | ${summary.boundaries.errors} | ${summary.boundaries.warnings} | ${(summary.boundaries.notes ?? []).join(', ')} |`,
    '',
    '## Policy',
    '',
    summary.blocking_reasons.length
      ? `Blocking reasons: ${summary.blocking_reasons.join(', ')}`
      : 'No blocking Fallow policy reasons.',
    summary.warnings.length ? `Warnings: ${summary.warnings.join(', ')}` : 'No warning buckets.',
    '',
    'Auto-fix policy: only `fallow fix --dry-run` is captured; no rewrite or delete action is executed.',
  ];
  const markdownPath = path.join(outputRoot, 'SUMMARY.md');
  fs.writeFileSync(markdownPath, `${lines.join('\n')}\n`, 'utf8');
  return markdownPath;
}

function main(): void {
  const outputRoot = path.resolve(REPO_ROOT, argValue('--output-dir', DEFAULT_OUTPUT_ROOT));
  fs.mkdirSync(outputRoot, { recursive: true });
  const runs = commandSpecs().map((spec) => runCommand(spec, outputRoot));
  const byName = new Map(runs.map((run) => [run.artifact.command, run]));
  const commandWarnings = runs
    .filter((run) => run.parse_error)
    .map((run) => `${run.artifact.command}:${run.parse_error}`);
  const rawArtifactText = runs
    .map((run) => {
      const stdout = fs.existsSync(path.join(REPO_ROOT, run.artifact.stdout_path))
        ? fs.readFileSync(path.join(REPO_ROOT, run.artifact.stdout_path), 'utf8')
        : '';
      const stderr = fs.existsSync(path.join(REPO_ROOT, run.artifact.stderr_path))
        ? fs.readFileSync(path.join(REPO_ROOT, run.artifact.stderr_path), 'utf8')
        : '';
      return `${stdout}\n${stderr}`;
    })
    .join('\n');
  const secretFindings = highConfidenceSecretFindings(rawArtifactText);
  const toolVersion =
    (byName.get('dead-code')?.parsed as { version?: string } | null)?.version ??
    (byName.get('dupes')?.parsed as { version?: string } | null)?.version ??
    'unknown';
  const partialSummary = {
    dead_code: deadCodeBucket(byName.get('dead-code')?.parsed),
    duplication: duplicationBucket(byName.get('dupes')?.parsed),
    health: healthBucket(byName.get('health')?.parsed),
    boundaries: boundaryBucket(byName.get('boundary-violations')?.parsed),
    secret_scan: {
      status: secretFindings.length > 0 ? 'fail' as const : 'pass' as const,
      findings: secretFindings,
    },
  };
  const verdict = computeVerdict(partialSummary);
  const summary: CodeIntelligenceSummary = {
    version: 'control-plane.code-intelligence/v1',
    generated_at: new Date().toISOString(),
    tool: 'fallow',
    tool_version: toolVersion,
    scope: 'apps/operator-panel',
    mode: process.env.CI ? 'ci' : 'repo_clean',
    telemetry_disabled:
      process.env.FALLOW_TELEMETRY_DISABLED === '1' || process.env.DO_NOT_TRACK === '1',
    ...partialSummary,
    verdict: verdict.verdict,
    baseline_used: fs.existsSync(path.join(REPO_ROOT, 'fallow-baselines', 'dead-code.json')),
    commands: runs.map((run) => run.artifact),
    artifacts: runs
      .flatMap((run) => [run.artifact.stdout_path, run.artifact.stderr_path, run.artifact.parsed_json_path])
      .filter((item): item is string => Boolean(item)),
    blocking_reasons: [...verdict.blockingReasons, ...commandWarnings.map(() => 'FALLOW_OUTPUT_INVALID')],
    warnings: [...verdict.warnings, ...commandWarnings],
  };
  const summaryPath = path.join(outputRoot, 'summary.json');
  writeJson(summaryPath, summary);
  const markdownPath = writeMarkdown(summary, outputRoot);
  summary.artifacts.push(relativeToRepo(REPO_ROOT, summaryPath), relativeToRepo(REPO_ROOT, markdownPath));
  writeJson(summaryPath, summary);
  process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
}

main();
