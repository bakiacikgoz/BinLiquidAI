import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

type JsonObject = Record<string, unknown>;

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = findRepoRoot(APP_ROOT);
const RESULTS_PATH = path.join(REPO_ROOT, 'artifacts', 'operator-panel-ui', 'e2e-json', 'results.json');
const REQUIRED_SPEC = 'no-raw-json-primary.spec.ts';

function findRepoRoot(start: string): string {
  let current = start;
  while (current !== path.dirname(current)) {
    if (fs.existsSync(path.join(current, 'pnpm-workspace.yaml')) || fs.existsSync(path.join(current, '.git'))) {
      return current;
    }
    current = path.dirname(current);
  }
  return start;
}

function fail(message: string): never {
  console.error(`No-primary-raw-JSON assertion failed: ${message}`);
  process.exit(1);
}

function asRecord(value: unknown): JsonObject {
  return typeof value === 'object' && value !== null ? (value as JsonObject) : {};
}

function walkSpecs(suite: JsonObject, rows: Array<{ file: string; title: string; passed: boolean }>): void {
  for (const spec of Array.isArray(suite.specs) ? suite.specs : []) {
    const specRecord = asRecord(spec);
    const tests = Array.isArray(specRecord.tests) ? specRecord.tests : [];
    const passed =
      tests.length > 0 &&
      tests.every((test) => {
        const testRecord = asRecord(test);
        return testRecord.status === 'expected' && testRecord.expectedStatus === 'passed';
      });
    rows.push({
      file: String(specRecord.file ?? ''),
      title: String(specRecord.title ?? ''),
      passed,
    });
  }

  for (const child of Array.isArray(suite.suites) ? suite.suites : []) {
    walkSpecs(asRecord(child), rows);
  }
}

if (!fs.existsSync(RESULTS_PATH)) {
  fail(`missing Playwright results at ${path.relative(REPO_ROOT, RESULTS_PATH)}`);
}

const payload = JSON.parse(fs.readFileSync(RESULTS_PATH, 'utf8')) as JsonObject;
const specs: Array<{ file: string; title: string; passed: boolean }> = [];
for (const suite of Array.isArray(payload.suites) ? payload.suites : []) {
  walkSpecs(asRecord(suite), specs);
}

const spec = specs.find((row) => row.file.endsWith(REQUIRED_SPEC));
if (!spec) {
  fail(`${REQUIRED_SPEC} did not run`);
}
if (!spec.passed) {
  fail(`${REQUIRED_SPEC} did not pass`);
}

console.log(
  JSON.stringify(
    {
      status: 'passed',
      spec: REQUIRED_SPEC,
      results: path.relative(REPO_ROOT, RESULTS_PATH),
    },
    null,
    2,
  ),
);
