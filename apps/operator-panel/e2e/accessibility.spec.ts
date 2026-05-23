import { expect, test, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';

import {
  e2eArtifactPath,
  gotoOperatorPanel,
  openPrimaryView,
  saveE2eScreenshot,
} from './helpers';

type AxeViolationSummary = {
  id: string;
  impact: string | null | undefined;
  help: string;
  nodes: Array<{
    target: string[];
    html: string;
    failureSummary?: string;
  }>;
};

type UnnamedControl = {
  tag: string;
  role: string;
  type: string;
  text: string;
  selector: string;
};

type KeyboardResult = {
  target: string;
  reached: boolean;
};

async function findUnnamedControls(page: Page): Promise<UnnamedControl[]> {
  return page.evaluate(() => {
    function isHiddenByAria(element: Element): boolean {
      return Boolean(element.closest('[aria-hidden="true"]'));
    }

    function isVisible(element: HTMLElement): boolean {
      const style = window.getComputedStyle(element);
      const rects = element.getClientRects();
      return style.display !== 'none' && style.visibility !== 'hidden' && rects.length > 0;
    }

    function textFromIds(ids: string): string {
      return ids
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent?.trim() ?? '')
        .filter(Boolean)
        .join(' ')
        .trim();
    }

    function labelText(element: HTMLElement): string {
      if (element instanceof HTMLInputElement || element instanceof HTMLSelectElement || element instanceof HTMLTextAreaElement) {
        return Array.from(element.labels ?? [])
          .map((label) => label.textContent?.trim() ?? '')
          .filter(Boolean)
          .join(' ')
          .trim();
      }
      return '';
    }

    function accessibleName(element: HTMLElement): string {
      const ariaLabel = element.getAttribute('aria-label')?.trim();
      if (ariaLabel) {
        return ariaLabel;
      }

      const ariaLabelledBy = element.getAttribute('aria-labelledby');
      if (ariaLabelledBy) {
        const labelledText = textFromIds(ariaLabelledBy);
        if (labelledText) {
          return labelledText;
        }
      }

      const labels = labelText(element);
      if (labels) {
        return labels;
      }

      const title = element.getAttribute('title')?.trim();
      if (title) {
        return title;
      }

      const placeholder = element.getAttribute('placeholder')?.trim();
      if (placeholder) {
        return placeholder;
      }

      return element.textContent?.trim() ?? '';
    }

    function selectorFor(element: HTMLElement): string {
      const tag = element.tagName.toLowerCase();
      const ariaLabel = element.getAttribute('aria-label');
      if (ariaLabel) {
        return `${tag}[aria-label="${ariaLabel}"]`;
      }
      const type = element.getAttribute('type');
      if (type) {
        return `${tag}[type="${type}"]`;
      }
      return tag;
    }

    return Array.from(
      document.querySelectorAll<HTMLElement>(
        'button, a[href], input:not([type="hidden"]), textarea, select, [role="button"], [role="link"], [role="textbox"], [role="combobox"]',
      ),
    )
      .filter((element) => !isHiddenByAria(element) && isVisible(element))
      .filter((element) => accessibleName(element).length === 0)
      .map((element) => ({
        tag: element.tagName.toLowerCase(),
        role: element.getAttribute('role') ?? '',
        type: element.getAttribute('type') ?? '',
        text: element.textContent?.trim() ?? '',
        selector: selectorFor(element),
      }));
  });
}

async function focusByKeyboard(page: Page, label: string): Promise<KeyboardResult> {
  for (let index = 0; index < 45; index += 1) {
    await page.keyboard.press('Tab');
    const focusedName = await page.evaluate(() => {
      const element = document.activeElement as HTMLElement | null;
      if (!element) {
        return '';
      }
      return [
        element.getAttribute('aria-label'),
        element.textContent,
        element.getAttribute('title'),
        element.getAttribute('placeholder'),
      ]
        .filter(Boolean)
        .join(' ')
        .trim();
    });

    if (focusedName.includes(label)) {
      return { target: label, reached: true };
    }
  }

  return { target: label, reached: false };
}

function writeAccessibilityReport({
  violations,
  unnamedControls,
  keyboardResults,
}: {
  violations: AxeViolationSummary[];
  unnamedControls: UnnamedControl[];
  keyboardResults: KeyboardResult[];
}) {
  const criticalViolations = violations.filter((violation) => violation.impact === 'critical');
  const report = {
    generatedAt: new Date().toISOString(),
    counts: {
      violations: violations.length,
      criticalViolations: criticalViolations.length,
      unnamedControls: unnamedControls.length,
      keyboardTargets: keyboardResults.length,
      keyboardFailures: keyboardResults.filter((result) => !result.reached).length,
    },
    criticalViolations,
    unnamedControls,
    keyboardResults,
  };

  fs.writeFileSync(e2eArtifactPath('accessibility', 'accessibility-report.json'), JSON.stringify(report, null, 2));
  fs.writeFileSync(
    e2eArtifactPath('accessibility', 'accessibility-report.md'),
    [
      '# Operator Panel Accessibility Smoke',
      '',
      `- Critical axe violations: ${report.counts.criticalViolations}`,
      `- Unnamed visible controls: ${report.counts.unnamedControls}`,
      `- Keyboard navigation failures: ${report.counts.keyboardFailures}`,
      '',
      '## Critical Violations',
      ...criticalViolations.map((violation) => `- ${violation.id}: ${violation.help}`),
      '',
      '## Unnamed Controls',
      ...unnamedControls.map((control) => `- ${control.selector} (${control.tag}${control.type ? `/${control.type}` : ''})`),
      '',
      '## Keyboard Targets',
      ...keyboardResults.map((result) => `- ${result.target}: ${result.reached ? 'pass' : 'fail'}`),
      '',
    ].join('\n'),
  );
}

test('workspace has no critical accessibility violations and visible controls are named', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });

  const accessibilityResults = await new AxeBuilder({ page }).analyze();
  const violations = accessibilityResults.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    nodes: violation.nodes.map((node) => ({
      target: node.target,
      html: node.html,
      failureSummary: node.failureSummary,
    })),
  }));
  const criticalViolations = violations.filter((violation) => violation.impact === 'critical');
  const unnamedControls = await findUnnamedControls(page);

  await saveE2eScreenshot(page, 'accessibility-workspace');
  writeAccessibilityReport({ violations, unnamedControls, keyboardResults: [] });

  expect(criticalViolations, JSON.stringify(criticalViolations, null, 2)).toEqual([]);
  expect(unnamedControls, JSON.stringify(unnamedControls, null, 2)).toEqual([]);
  consoleHealth.assertNoCriticalErrors();
});

test('primary navigation is reachable with keyboard activation', async ({ page }) => {
  const consoleHealth = await gotoOperatorPanel(page, { operatorId: 'qa-operator' });
  const keyboardResults: KeyboardResult[] = [];

  const tasksFocus = await focusByKeyboard(page, 'Görevler');
  keyboardResults.push(tasksFocus);
  expect(tasksFocus.reached).toBe(true);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Tasks', exact: true })).toBeVisible();

  await openPrimaryView(page, 'Mission Control', 'Mission Control');
  const settingsFocus = await focusByKeyboard(page, 'Ayarlar');
  keyboardResults.push(settingsFocus);
  expect(settingsFocus.reached).toBe(true);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('heading', { name: 'Settings', exact: true })).toBeVisible();

  writeAccessibilityReport({ violations: [], unnamedControls: [], keyboardResults });
  consoleHealth.assertNoCriticalErrors();
});
