import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

import { routeGroups, routes } from '../src/routeRegistry';

type Manifest = {
  aliasViews?: unknown[];
  consoleMessages?: unknown[];
  pageErrors?: unknown[];
  pages?: Array<{
    routeId?: string;
    nav?: string;
    heading?: string;
    screenshot?: string;
  }>;
};

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const APP_ROOT = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = findRepoRoot(APP_ROOT);
const MANIFEST_PATH = path.join(REPO_ROOT, 'artifacts', 'operator-panel-ui', 'productized-pages', 'manifest.json');

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
  console.error(`Productization assertion failed: ${message}`);
  process.exit(1);
}

function unique(values: string[], label: string): void {
  const duplicates = values.filter((value, index) => values.indexOf(value) !== index);
  if (duplicates.length > 0) {
    fail(`${label} must be unique: ${Array.from(new Set(duplicates)).join(', ')}`);
  }
}

unique(routes.map((route) => route.routeId), 'route ids');
unique(routes.map((route) => route.label), 'route labels');
unique(routes.map((route) => route.heading), 'route headings');
unique(routes.map((route) => route.id), 'nav ids');

for (const group of routeGroups) {
  if (group.routes.length === 0) {
    fail(`route group ${group.title} has no routes`);
  }
}

if (!fs.existsSync(MANIFEST_PATH)) {
  fail(`missing Playwright productization manifest at ${path.relative(REPO_ROOT, MANIFEST_PATH)}`);
}

const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8')) as Manifest;
if ((manifest.aliasViews ?? []).length > 0) {
  fail('manifest contains aliasViews');
}
if ((manifest.consoleMessages ?? []).length > 0) {
  fail('manifest contains console messages');
}
if ((manifest.pageErrors ?? []).length > 0) {
  fail('manifest contains page errors');
}

const pages = manifest.pages ?? [];
if (pages.length !== routes.length) {
  fail(`manifest page count ${pages.length} does not match route count ${routes.length}`);
}

unique(
  pages.map((page) => String(page.routeId ?? '')),
  'manifest route ids',
);
unique(
  pages.map((page) => String(page.nav ?? '')),
  'manifest nav labels',
);
unique(
  pages.map((page) => String(page.heading ?? '')),
  'manifest headings',
);

for (const page of pages) {
  if (!page.routeId || !page.nav || !page.heading || !page.screenshot) {
    fail(`manifest page is incomplete: ${JSON.stringify(page)}`);
  }
  if (!fs.existsSync(page.screenshot)) {
    fail(`missing screenshot for ${page.routeId}: ${page.screenshot}`);
  }
}

console.log(
  JSON.stringify(
    {
      status: 'passed',
      routeCount: routes.length,
      manifest: path.relative(REPO_ROOT, MANIFEST_PATH),
    },
    null,
    2,
  ),
);
