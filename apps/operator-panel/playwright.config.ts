import { defineConfig, devices } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

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

const e2eDir = path.resolve(process.cwd(), 'e2e');
const hasE2eSpecs =
  fs.existsSync(e2eDir) &&
  fs.readdirSync(e2eDir).some((file) => /\.(spec|test)\.[cm]?[jt]s$/.test(file) || /\.(spec|test)\.tsx$/.test(file));
const artifactRoot = path.join(findRepoRoot(process.cwd()), 'artifacts', 'operator-panel-ui');

export default defineConfig({
  testDir: './e2e',
  outputDir: path.join(artifactRoot, 'e2e-results'),
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['json', { outputFile: path.join(artifactRoot, 'e2e-json', 'results.json') }],
    ['html', { outputFolder: path.join(artifactRoot, 'e2e-report'), open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: hasE2eSpecs
    ? {
        command: 'node scripts/start-preview-server.mjs',
        url: 'http://127.0.0.1:5173',
        reuseExistingServer: true,
        timeout: 120_000,
      }
    : undefined,
});
