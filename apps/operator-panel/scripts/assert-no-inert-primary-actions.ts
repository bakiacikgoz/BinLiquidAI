import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { routes } from '../src/routeRegistry';
import { routeCapabilityMatrix } from '../src/routeCapabilityMatrix';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(SCRIPT_DIR, '..');
const SRC_ROOT = path.join(APP_ROOT, 'src');

function fail(message: string): never {
  console.error(`No-inert-primary-actions assertion failed: ${message}`);
  process.exit(1);
}

function walkFiles(root: string): string[] {
  const entries = fs.readdirSync(root, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      if (!['node_modules', 'dist', 'coverage'].includes(entry.name)) {
        files.push(...walkFiles(fullPath));
      }
      continue;
    }
    if (/\.(tsx?|jsx?)$/.test(entry.name) && !entry.name.endsWith('.test.tsx')) {
      files.push(fullPath);
    }
  }
  return files;
}

const routeIds = new Set(routes.map((route) => route.routeId));
const matrixIds = new Set(routeCapabilityMatrix.map((route) => route.routeId));

for (const routeId of routeIds) {
  if (!matrixIds.has(routeId)) {
    fail(`missing route capability for ${routeId}`);
  }
}
for (const route of routeCapabilityMatrix) {
  if (!routeIds.has(route.routeId)) {
    fail(`unknown route capability ${route.routeId}`);
  }
  for (const action of route.primaryActions) {
    if (action.noShipIfInert !== true) {
      fail(`${route.routeId}.${action.actionId} must be noShipIfInert`);
    }
    if (action.state === 'working' && !action.bridgeCommand && !action.cliCommand) {
      fail(`${route.routeId}.${action.actionId} is working but has no bridge/CLI command`);
    }
    if (action.state === 'disabled_with_reason' && !action.disabledReasonCode) {
      fail(`${route.routeId}.${action.actionId} is disabled without a reason code`);
    }
  }
}

const inertPatterns = [
  /onClick=\{\s*\(\)\s*=>\s*\{\s*\}\s*\}/,
  /onClick=\{\s*async\s*\(\)\s*=>\s*\{\s*\}\s*\}/,
  /TODO:\s*(wire|implement|connect)/i,
];
const findings: Array<{ file: string; pattern: string }> = [];
for (const file of walkFiles(SRC_ROOT)) {
  const text = fs.readFileSync(file, 'utf8');
  for (const pattern of inertPatterns) {
    if (pattern.test(text)) {
      findings.push({ file: path.relative(APP_ROOT, file), pattern: String(pattern) });
    }
  }
}
if (findings.length > 0) {
  fail(`inert action markers found: ${JSON.stringify(findings)}`);
}

console.log(
  JSON.stringify(
    {
      status: 'passed',
      routeCount: routeCapabilityMatrix.length,
      primaryActionCount: routeCapabilityMatrix.reduce(
        (total, route) => total + route.primaryActions.length,
        0,
      ),
    },
    null,
    2,
  ),
);
