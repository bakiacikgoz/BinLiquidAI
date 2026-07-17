import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

import { installFormArtifactBridgeStub } from './artifact-helpers';
import { gotoOperatorPanel, openPrimaryView } from './helpers';

const SENSITIVE_RESPONSE = 'phase-13-sensitive-form-canary';

test('governed form stays CSP-safe, memory-only, explicit, and approval-bound', async ({ page }) => {
  test.setTimeout(90_000);
  const responseHeaders: string[] = [];
  const unexpectedRequests: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (!url.startsWith('http://127.0.0.1:5173') && !url.startsWith('blob:') && !url.startsWith('data:')) {
      unexpectedRequests.push(url);
    }
  });
  page.on('response', (response) => {
    if (response.request().resourceType() === 'document') {
      responseHeaders.push(response.headers()['content-security-policy'] ?? '');
    }
  });
  await page.addInitScript(() => {
    window.addEventListener('securitypolicyviolation', (event) => {
      const evidence = document.createElement('meta');
      evidence.setAttribute('name', 'artifact-csp-violation');
      evidence.setAttribute('content', JSON.stringify({
        directive: event.violatedDirective,
        blockedUri: event.blockedURI,
        sourceFile: event.sourceFile,
        lineNumber: event.lineNumber,
        columnNumber: event.columnNumber,
        sample: event.sample,
      }));
      document.head.append(evidence);
    });
  });
  await installFormArtifactBridgeStub(page);
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'form-operator' });
  expect(responseHeaders[0]).toContain("script-src 'self'");
  expect(responseHeaders[0]).not.toContain("'unsafe-eval'");
  await openPrimaryView(page, 'AI Assistant', 'Welcome to ImperaOS Assistant');
  await page.getByLabel('Message').fill('Open a governed form artifact.');
  await page.getByLabel('Message').press('Enter');
  await page.keyboard.press('F8');
  const openForm = page.getByRole('button', { name: 'Open Intake form' });
  await expect(openForm).toBeVisible();
  const inlineForm = page.getByRole('region', { name: 'Inline form: Intake form' });
  await expect(inlineForm).toBeVisible({ timeout: 30_000 });
  await page.context().setOffline(true);
  const inlineField = inlineForm.getByLabel('Name');
  await expect(inlineField).toHaveAttribute('type', 'password');
  await inlineField.fill(SENSITIVE_RESPONSE);
  await inlineForm.getByRole('button', { name: 'Expand in Workbench' }).click();
  const workbench = page.getByRole('complementary', { name: 'Workbench' });
  const field = workbench.getByLabel('Name');
  await expect(field).toBeVisible({ timeout: 30_000 });
  await expect(field).toHaveAttribute('type', 'password');
  await expect(field).toHaveValue(SENSITIVE_RESPONSE);
  await expect(workbench.getByRole('button', { name: 'Submit form' })).toBeVisible();

  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOMStorage.enable');
  const securityOrigin = new URL(page.url()).origin;
  const localStorage = await cdp.send('DOMStorage.getDOMStorageItems', {
    storageId: { securityOrigin, isLocalStorage: true },
  });
  const sessionStorage = await cdp.send('DOMStorage.getDOMStorageItems', {
    storageId: { securityOrigin, isLocalStorage: false },
  });
  expect(JSON.stringify({ localStorage, sessionStorage })).not.toContain(SENSITIVE_RESPONSE);

  const accessibility = await new AxeBuilder({ page }).include('.assistant-workbench').analyze();
  expect(
    accessibility.violations.filter((violation) => violation.impact === 'critical'),
    JSON.stringify(accessibility.violations, null, 2),
  ).toEqual([]);

  await workbench.getByRole('button', { name: 'Submit form' }).click();
  await expect(workbench.getByText('Form submitted and awaiting approval.', { exact: true })).toBeVisible();
  const submissionEvidence = page.locator('meta[name="artifact-form-submission"]');
  await expect(submissionEvidence).toHaveCount(1);
  const submission = JSON.parse(await submissionEvidence.getAttribute('content') ?? '{}') as Record<string, unknown>;
  expect(submission).toMatchObject({
    artifactId: 'artifact-preview-form', schemaRevisionId: 'form-revision-1',
    response: { name: SENSITIVE_RESPONSE }, persistencePolicy: 'none',
  });
  expect(submission).not.toHaveProperty('approvalGranted');
  const violationEvidence = page.locator('meta[name="artifact-csp-violation"]');
  const violationCount = await violationEvidence.count();
  const violationDetail = violationCount > 0 ? await violationEvidence.first().getAttribute('content') : '';
  expect(violationCount, violationDetail ?? '').toBe(0);
  expect(unexpectedRequests).toEqual([]);
  consoleHealth.assertNoCriticalErrors();
});
