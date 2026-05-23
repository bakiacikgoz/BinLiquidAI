import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import ts from 'typescript';

type UiControlKind =
  | 'button'
  | 'link'
  | 'tab'
  | 'input'
  | 'select'
  | 'checkbox'
  | 'textarea'
  | 'menu-item'
  | 'quick-action';

type UiControlRisk =
  | 'read_only'
  | 'state_change'
  | 'bridge_read'
  | 'bridge_mutation'
  | 'destructive_or_sensitive'
  | 'debug_or_raw_payload';

type UiControlStatus =
  | 'wired'
  | 'disabled_with_reason'
  | 'intentionally_static'
  | 'missing_handler'
  | 'noop_handler'
  | 'unknown_handler'
  | 'needs_manual_review';

type FindingSeverity = 'Critical' | 'High' | 'Medium' | 'Low';

type UiControlInventoryItem = {
  id: string;
  file: string;
  line: number;
  component: string;
  kind: UiControlKind;
  accessibleName: string;
  visibleText: string;
  handlerName: string | null;
  disabledExpression: string | null;
  disabledReasonExpression: string | null;
  bridgeFunction: string | null;
  risk: UiControlRisk;
  status: UiControlStatus;
  requiresTest: boolean;
  notes: string[];
};

type UiControlFinding = {
  severity: FindingSeverity;
  rule: string;
  controlId: string;
  file: string;
  line: number;
  message: string;
};

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const APP_ROOT = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = findRepoRoot(APP_ROOT);
const SRC_ROOT = path.join(APP_ROOT, 'src');
const OUTPUT_ROOT = resolveOutputRoot();
const BRIDGE_FILE = path.join(SRC_ROOT, 'bridge.ts');

const INTERACTIVE_TAGS = new Set(['button', 'a', 'input', 'select', 'textarea', 'Button']);
const BRIDGE_MUTATION_PREFIXES = [
  'decide',
  'execute',
  'submit',
  'resume',
  'pause',
  'stop',
  'export',
  'create',
  'verify',
  'plan',
  'dryRun',
  'run',
  'rotate',
];
const BRIDGE_READ_PREFIXES = ['fetch', 'get', 'list', 'resolve', 'check', 'snapshot', 'handshake', 'read', 'tail'];
const DESTRUCTIVE_TOKENS = [
  'approve',
  'approval',
  'reject',
  'execute',
  'cancel',
  'delete',
  'remove',
  'stop',
  'start',
  'resume',
  'pause',
  'export',
  'backup',
  'restore',
  'migration',
  'migrate',
  'rotate',
  'key',
  'support',
  'qualification',
  'computer-use',
  'computer use',
  'onay',
  'reddet',
  'iptal',
  'durdur',
  'baslat',
  'calistir',
  'yurut',
  'yedek',
  'geri yukle',
  'disari aktar',
];
const RAW_DEBUG_TOKENS = ['raw', 'debug', 'json', 'payload', 'stderr', 'secret', 'token'];

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

function resolveOutputRoot(): string {
  const preferred = path.join(REPO_ROOT, 'artifacts', 'operator-panel-ui');
  const fallback = path.join(APP_ROOT, 'artifacts', 'operator-panel-ui');
  return canWriteDirectory(preferred) ? preferred : fallback;
}

function canWriteDirectory(directory: string): boolean {
  try {
    fs.mkdirSync(directory, { recursive: true });
    const probe = path.join(directory, '.write-test');
    fs.writeFileSync(probe, '');
    fs.unlinkSync(probe);
    return true;
  } catch {
    return false;
  }
}

function walkFiles(root: string): string[] {
  const entries = fs.readdirSync(root, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = path.join(root, entry.name);
    if (entry.isDirectory()) {
      return walkFiles(fullPath);
    }
    if (!entry.name.endsWith('.tsx')) {
      return [];
    }
    if (entry.name.includes('.test.') || entry.name.includes('.interaction.') || entry.name.includes('.integration.')) {
      return [];
    }
    return [fullPath];
  });
}

function readBridgeFunctionNames(): string[] {
  if (!fs.existsSync(BRIDGE_FILE)) {
    return [];
  }
  const source = fs.readFileSync(BRIDGE_FILE, 'utf8');
  return Array.from(source.matchAll(/export\s+async\s+function\s+([A-Za-z0-9_]+)/g)).map((match) => match[1]);
}

function attributeMap(node: ts.JsxOpeningLikeElement, source: ts.SourceFile): Map<string, string | true> {
  const attrs = new Map<string, string | true>();
  for (const attr of node.attributes.properties) {
    if (ts.isJsxSpreadAttribute(attr)) {
      attrs.set('...spread', attr.expression.getText(source));
      continue;
    }
    const name = attr.name.getText(source);
    if (!attr.initializer) {
      attrs.set(name, true);
      continue;
    }
    if (ts.isStringLiteral(attr.initializer)) {
      attrs.set(name, attr.initializer.text);
      continue;
    }
    if (ts.isJsxExpression(attr.initializer)) {
      attrs.set(name, attr.initializer.expression?.getText(source) ?? '');
      continue;
    }
    attrs.set(name, attr.initializer.getText(source));
  }
  return attrs;
}

function attr(attrs: Map<string, string | true>, name: string): string | null {
  const value = attrs.get(name);
  if (value === undefined) {
    return null;
  }
  return value === true ? 'true' : value;
}

function collectText(node: ts.Node): string {
  const parts: string[] = [];
  function visitText(child: ts.Node): void {
    if (ts.isJsxText(child)) {
      const text = child.getText().replace(/\s+/g, ' ').trim();
      if (text) {
        parts.push(text);
      }
      return;
    }
    if (ts.isStringLiteral(child) || ts.isNoSubstitutionTemplateLiteral(child)) {
      parts.push(child.text);
      return;
    }
    child.forEachChild(visitText);
  }
  node.forEachChild(visitText);
  return parts.join(' ').replace(/\s+/g, ' ').trim();
}

function getTagName(node: ts.JsxOpeningLikeElement, source: ts.SourceFile): string {
  return node.tagName.getText(source);
}

function isControl(node: ts.JsxOpeningLikeElement, source: ts.SourceFile, attrs: Map<string, string | true>): boolean {
  const tag = getTagName(node, source);
  if (INTERACTIVE_TAGS.has(tag)) {
    return true;
  }
  const role = attr(attrs, 'role');
  return role === 'tab' || role === 'menuitem' || tag.endsWith('Button');
}

function getKind(node: ts.JsxOpeningLikeElement, source: ts.SourceFile, attrs: Map<string, string | true>): UiControlKind {
  const tag = getTagName(node, source);
  const role = attr(attrs, 'role');
  const className = attr(attrs, 'className') ?? '';
  if (role === 'tab' || className.toLowerCase().includes('tab')) {
    return 'tab';
  }
  if (role === 'menuitem') {
    return 'menu-item';
  }
  if (tag === 'a') {
    return 'link';
  }
  if (tag === 'select') {
    return 'select';
  }
  if (tag === 'textarea') {
    return 'textarea';
  }
  if (tag === 'input') {
    return attr(attrs, 'type') === 'checkbox' ? 'checkbox' : 'input';
  }
  if (className.toLowerCase().includes('quick')) {
    return 'quick-action';
  }
  return 'button';
}

function findHandler(kind: UiControlKind, attrs: Map<string, string | true>): string | null {
  const candidates =
    kind === 'input' || kind === 'select' || kind === 'checkbox' || kind === 'textarea'
      ? ['onChange', 'onInput', 'onClick']
      : ['onClick', 'onSubmit', 'onChange'];
  for (const name of candidates) {
    const value = attr(attrs, name);
    if (value) {
      return value;
    }
  }
  if (kind === 'link' && attr(attrs, 'href')) {
    return `href:${attr(attrs, 'href')}`;
  }
  return null;
}

function isNoop(handler: string | null): boolean {
  if (!handler) {
    return false;
  }
  const normalized = handler.replace(/\s+/g, '');
  return (
    normalized === 'noop' ||
    normalized === '()=>undefined' ||
    normalized === '()=>{}' ||
    normalized === 'function(){}' ||
    normalized === 'functionnoop(){}'
  );
}

function nearestAccessibleName(
  attrs: Map<string, string | true>,
  visibleText: string,
  kind: UiControlKind,
): string {
  return (
    attr(attrs, 'aria-label') ??
    attr(attrs, 'title') ??
    visibleText ??
    attr(attrs, 'placeholder') ??
    attr(attrs, 'name') ??
    (kind === 'checkbox' ? attr(attrs, 'value') : null) ??
    ''
  );
}

function inferBridgeFunction(sourceText: string, bridgeFunctions: string[]): string | null {
  const normalized = sourceText.toLowerCase();
  const matched = bridgeFunctions.find((name) => normalized.includes(name.toLowerCase()));
  return matched ?? null;
}

function inferRisk(itemText: string, bridgeFunction: string | null, hasHandler: boolean): UiControlRisk {
  const normalized = itemText.toLowerCase();
  if (RAW_DEBUG_TOKENS.some((token) => normalized.includes(token))) {
    return 'debug_or_raw_payload';
  }
  if (DESTRUCTIVE_TOKENS.some((token) => normalized.includes(token))) {
    return 'destructive_or_sensitive';
  }
  if (bridgeFunction) {
    if (BRIDGE_MUTATION_PREFIXES.some((prefix) => bridgeFunction.startsWith(prefix))) {
      return 'bridge_mutation';
    }
    if (BRIDGE_READ_PREFIXES.some((prefix) => bridgeFunction.startsWith(prefix))) {
      return 'bridge_read';
    }
  }
  return hasHandler ? 'state_change' : 'read_only';
}

function statusFor(
  kind: UiControlKind,
  handlerName: string | null,
  disabledExpression: string | null,
  disabledReasonExpression: string | null,
  hasSpread: boolean,
  attrs: Map<string, string | true>,
): UiControlStatus {
  if (isNoop(handlerName)) {
    return 'noop_handler';
  }
  if (attr(attrs, 'type') === 'submit') {
    return 'wired';
  }
  if (disabledExpression && disabledReasonExpression) {
    return 'disabled_with_reason';
  }
  if (disabledExpression) {
    return 'needs_manual_review';
  }
  if (handlerName) {
    return disabledExpression && disabledReasonExpression ? 'disabled_with_reason' : 'wired';
  }
  if (hasSpread) {
    return 'unknown_handler';
  }
  if (kind === 'link' && attr(attrs, 'href')) {
    return 'wired';
  }
  if (kind === 'input' || kind === 'select' || kind === 'checkbox' || kind === 'textarea') {
    return attr(attrs, 'readOnly') || attr(attrs, 'disabled') ? 'intentionally_static' : 'missing_handler';
  }
  return 'missing_handler';
}

function shouldRequireTest(risk: UiControlRisk, status: UiControlStatus): boolean {
  return (
    risk === 'bridge_mutation' ||
    risk === 'destructive_or_sensitive' ||
    risk === 'debug_or_raw_payload' ||
    status === 'missing_handler' ||
    status === 'noop_handler' ||
    status === 'unknown_handler'
  );
}

function auditFile(filePath: string, bridgeFunctions: string[]): UiControlInventoryItem[] {
  const sourceText = fs.readFileSync(filePath, 'utf8');
  const source = ts.createSourceFile(filePath, sourceText, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const controls: UiControlInventoryItem[] = [];
  const relativeFile = path.relative(REPO_ROOT, filePath);

  function visit(node: ts.Node, component: string): void {
    let nextComponent = component;
    if (ts.isFunctionDeclaration(node) && node.name && /^[A-Z]/.test(node.name.text)) {
      nextComponent = node.name.text;
    }
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && /^[A-Z]/.test(node.name.text)) {
      nextComponent = node.name.text;
    }

    if (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) {
      const attrs = attributeMap(node, source);
      if (isControl(node, source, attrs)) {
        const kind = getKind(node, source, attrs);
        const parent = ts.isJsxOpeningElement(node) ? node.parent : node;
        const visibleText = collectText(parent);
        const handlerName = findHandler(kind, attrs);
        const disabledExpression = attr(attrs, 'disabled') ?? attr(attrs, 'aria-disabled');
        const disabledReasonExpression =
          attr(attrs, 'title') ?? attr(attrs, 'aria-describedby') ?? attr(attrs, 'data-disabled-reason');
        const line = source.getLineAndCharacterOfPosition(node.getStart(source)).line + 1;
        const fullControlText = `${visibleText} ${handlerName ?? ''} ${node.getText(source)}`;
        const bridgeFunction = inferBridgeFunction(fullControlText, bridgeFunctions);
        const risk = inferRisk(fullControlText, bridgeFunction, Boolean(handlerName));
        const hasSpread = attrs.has('...spread');
        const status = statusFor(kind, handlerName, disabledExpression, disabledReasonExpression, hasSpread, attrs);
        const accessibleName = nearestAccessibleName(attrs, visibleText, kind);
        const notes: string[] = [];

        if (hasSpread) {
          notes.push('Props are spread into this control; handler requires manual review.');
        }
        if (disabledExpression && !disabledReasonExpression) {
          notes.push('Disabled expression is present without an explicit reason surface.');
        }
        if (!accessibleName) {
          notes.push('No accessible name inferred from aria-label, title, visible text, placeholder, or name.');
        }

        controls.push({
          id: `${relativeFile}:${line}:${controls.length + 1}`,
          file: relativeFile,
          line,
          component: nextComponent || 'Unknown',
          kind,
          accessibleName,
          visibleText,
          handlerName,
          disabledExpression,
          disabledReasonExpression,
          bridgeFunction,
          risk,
          status,
          requiresTest: shouldRequireTest(risk, status),
          notes,
        });
      }
    }

    node.forEachChild((child) => visit(child, nextComponent));
  }

  visit(source, 'Unknown');
  return controls;
}

function buildFindings(controls: UiControlInventoryItem[]): UiControlFinding[] {
  const findings: UiControlFinding[] = [];
  for (const control of controls) {
    if (control.status === 'missing_handler' && ['button', 'tab', 'menu-item', 'quick-action'].includes(control.kind)) {
      findings.push({
        severity: 'High',
        rule: 'missing-handler',
        controlId: control.id,
        file: control.file,
        line: control.line,
        message: `${control.kind} has no explicit handler or spread props.`,
      });
    }
    if (control.status === 'noop_handler') {
      findings.push({
        severity: 'High',
        rule: 'noop-handler',
        controlId: control.id,
        file: control.file,
        line: control.line,
        message: `${control.kind} is wired to a no-op handler.`,
      });
    }
    if (control.disabledExpression && !control.disabledReasonExpression) {
      findings.push({
        severity: 'Medium',
        rule: 'disabled-without-reason',
        controlId: control.id,
        file: control.file,
        line: control.line,
        message: `${control.kind} has disabled state without title, aria-describedby, or data-disabled-reason.`,
      });
    }
    if (!control.accessibleName) {
      findings.push({
        severity: 'Medium',
        rule: 'missing-accessible-name',
        controlId: control.id,
        file: control.file,
        line: control.line,
        message: `${control.kind} has no inferred accessible name.`,
      });
    }
    if (control.risk === 'debug_or_raw_payload' && !/confirm|onConfirm|showRaw|debugRaw/i.test(control.handlerName ?? '')) {
      findings.push({
        severity: 'Low',
        rule: 'raw-debug-manual-review',
        controlId: control.id,
        file: control.file,
        line: control.line,
        message: `${control.kind} references raw/debug payload text and needs manual disclosure review.`,
      });
    }
  }
  return findings;
}

function severityCount(findings: UiControlFinding[], severity: FindingSeverity): number {
  return findings.filter((finding) => finding.severity === severity).length;
}

function writeMarkdown(controls: UiControlInventoryItem[], findings: UiControlFinding[]): void {
  const highOrCritical = findings.filter((finding) => finding.severity === 'High' || finding.severity === 'Critical');
  const medium = findings.filter((finding) => finding.severity === 'Medium');
  const lines = [
    '# Operator Panel UI Control Audit',
    '',
    `Generated: ${new Date().toISOString()}`,
    `Total controls: ${controls.length}`,
    `Critical findings: ${severityCount(findings, 'Critical')}`,
    `High findings: ${severityCount(findings, 'High')}`,
    `Medium findings: ${severityCount(findings, 'Medium')}`,
    '',
    '## Gate Findings',
    '',
  ];

  if (highOrCritical.length === 0) {
    lines.push('No Critical or High dead-control findings.');
  } else {
    lines.push('| Severity | Rule | Location | Message |');
    lines.push('|---|---|---|---|');
    for (const finding of highOrCritical) {
      lines.push(
        `| ${finding.severity} | ${finding.rule} | ${finding.file}:${finding.line} | ${finding.message} |`,
      );
    }
  }

  lines.push('', '## Medium Findings', '');
  if (medium.length === 0) {
    lines.push('No Medium findings.');
  } else {
    lines.push('| Rule | Location | Message |');
    lines.push('|---|---|---|');
    for (const finding of medium) {
      lines.push(`| ${finding.rule} | ${finding.file}:${finding.line} | ${finding.message} |`);
    }
  }

  fs.writeFileSync(path.join(OUTPUT_ROOT, 'dead-controls.md'), `${lines.join('\n')}\n`);

  const inventoryLines = [
    '# Operator Panel UI Control Inventory',
    '',
    `Generated: ${new Date().toISOString()}`,
    '',
    '| Kind | Status | Risk | Location | Name | Handler |',
    '|---|---|---|---|---|---|',
    ...controls.map((control) =>
      [
        control.kind,
        control.status,
        control.risk,
        `${control.file}:${control.line}`,
        escapePipe(control.accessibleName || control.visibleText || '-'),
        escapePipe(control.handlerName ?? '-'),
      ].join(' | '),
    ),
  ];
  fs.writeFileSync(path.join(OUTPUT_ROOT, 'control-inventory.md'), `${inventoryLines.join('\n')}\n`);
}

function writeQaSummary(controls: UiControlInventoryItem[], findings: UiControlFinding[]): void {
  const summary = {
    generatedAtUtc: new Date().toISOString(),
    commit: readGitHead(),
    packageVersion: readPackageVersion(),
    totalControls: controls.length,
    testedControls: controls.filter((control) => !control.requiresTest).length,
    untestedControls: controls.filter((control) => control.requiresTest).length,
    deadControls: findings.filter((finding) => finding.rule === 'missing-handler' || finding.rule === 'noop-handler')
      .length,
    missingHandlers: controls.filter((control) => control.status === 'missing_handler').length,
    noopHandlers: controls.filter((control) => control.status === 'noop_handler').length,
    disabledWithoutReason: findings.filter((finding) => finding.rule === 'disabled-without-reason').length,
    bridgeBoundControls: controls.filter((control) => control.bridgeFunction).length,
    bridgeMutationControls: controls.filter((control) => control.risk === 'bridge_mutation').length,
    criticalFindings: severityCount(findings, 'Critical'),
    highFindings: severityCount(findings, 'High'),
    mediumFindings: severityCount(findings, 'Medium'),
    lowFindings: severityCount(findings, 'Low'),
    testSuites: {
      unit: 'skipped',
      interaction: 'skipped',
      e2e: 'skipped',
      accessibility: 'skipped',
      responsive: 'skipped',
      build: 'skipped',
      lint: 'skipped',
    },
    blockers: findings
      .filter((finding) => finding.severity === 'Critical' || finding.severity === 'High')
      .map((finding) => `${finding.rule}: ${finding.file}:${finding.line}`),
  };
  fs.writeFileSync(path.join(OUTPUT_ROOT, 'qa-summary.json'), `${JSON.stringify(summary, null, 2)}\n`);

  const markdown = [
    '# Operator Panel Frontend QA Summary',
    '',
    `Generated: ${summary.generatedAtUtc}`,
    `Commit: ${summary.commit ?? 'unknown'}`,
    `Package version: ${summary.packageVersion}`,
    '',
    `Total controls: ${summary.totalControls}`,
    `Requires manual/test coverage: ${summary.untestedControls}`,
    `Critical findings: ${summary.criticalFindings}`,
    `High findings: ${summary.highFindings}`,
    `Medium findings: ${summary.mediumFindings}`,
    '',
    summary.blockers.length > 0 ? '## Blockers' : '## Blockers',
    '',
    summary.blockers.length > 0 ? summary.blockers.map((blocker) => `- ${blocker}`).join('\n') : 'No gate blockers.',
  ];
  fs.writeFileSync(path.join(OUTPUT_ROOT, 'qa-summary.md'), `${markdown.join('\n')}\n`);
}

function writeManualChecklist(): void {
  const checklist = [
    '# Operator Panel Manual Exploratory Checklist',
    '',
    '| Area | Check | Result | Notes |',
    '|---|---|---|---|',
    '| Workspace | First screen content is clear and honest. | Not run | |',
    '| Sidebar | Every menu opens the expected view. | Not run | |',
    '| Top Refresh | Refresh gives visible feedback. | Not run | |',
    '| Tasks | Empty submit is safely blocked. | Not run | |',
    '| Tasks | Valid submit gives success or safe error feedback. | Not run | |',
    '| Approvals | Mutations stay disabled without operator ID. | Not run | |',
    '| Runs | Run selection, tabs, and export are wired. | Not run | |',
    '| System | Doctor, config, and capabilities are readable. | Not run | |',
    '| Operations | Each tab action updates output through mock/preview. | Not run | |',
    '| Settings | Saved settings persist after reload. | Not run | |',
    '| Computer-use | Start remains disabled when not qualified. | Not run | |',
    '| Debug Raw | Raw payload requires explicit confirmation. | Not run | |',
    '| Error UX | Bridge errors are safe and actionable. | Not run | |',
    '| Mobile | Navigation and primary CTAs are usable. | Not run | |',
    '| Keyboard | Core flows work without a mouse. | Not run | |',
  ];
  fs.writeFileSync(path.join(OUTPUT_ROOT, 'manual-exploratory-checklist.md'), `${checklist.join('\n')}\n`);
}

function readGitHead(): string | null {
  const headPath = path.join(REPO_ROOT, '.git', 'HEAD');
  if (!fs.existsSync(headPath)) {
    return null;
  }
  const head = fs.readFileSync(headPath, 'utf8').trim();
  if (!head.startsWith('ref:')) {
    return head;
  }
  const ref = head.slice('ref:'.length).trim();
  const refPath = path.join(REPO_ROOT, '.git', ref);
  return fs.existsSync(refPath) ? fs.readFileSync(refPath, 'utf8').trim() : null;
}

function readPackageVersion(): string {
  const packageJson = JSON.parse(fs.readFileSync(path.join(APP_ROOT, 'package.json'), 'utf8')) as {
    version?: string;
  };
  return packageJson.version ?? 'unknown';
}

function escapePipe(value: string): string {
  return value.replace(/\|/g, '\\|').replace(/\s+/g, ' ').trim();
}

function main(): void {
  fs.mkdirSync(OUTPUT_ROOT, { recursive: true });
  const bridgeFunctions = readBridgeFunctionNames();
  const controls = walkFiles(SRC_ROOT).flatMap((filePath) => auditFile(filePath, bridgeFunctions));
  const findings = buildFindings(controls);
  const summary = {
    generatedAtUtc: new Date().toISOString(),
    sourceRoot: path.relative(REPO_ROOT, SRC_ROOT),
    totalControls: controls.length,
    missingHandlers: controls.filter((control) => control.status === 'missing_handler').length,
    noopHandlers: controls.filter((control) => control.status === 'noop_handler').length,
    disabledWithoutReason: findings.filter((finding) => finding.rule === 'disabled-without-reason').length,
    needsManualReview: controls.filter((control) => control.status === 'unknown_handler' || control.requiresTest).length,
    criticalFindings: severityCount(findings, 'Critical'),
    highFindings: severityCount(findings, 'High'),
    mediumFindings: severityCount(findings, 'Medium'),
    lowFindings: severityCount(findings, 'Low'),
  };

  fs.writeFileSync(
    path.join(OUTPUT_ROOT, 'control-inventory.json'),
    `${JSON.stringify({ ...summary, controls, findings }, null, 2)}\n`,
  );
  writeMarkdown(controls, findings);
  writeQaSummary(controls, findings);
  writeManualChecklist();

  console.log(
    `UI control audit: ${summary.totalControls} controls, ${summary.criticalFindings} critical, ${summary.highFindings} high, ${summary.mediumFindings} medium`,
  );

  if (summary.criticalFindings > 0 || summary.highFindings > 0) {
    process.exitCode = 1;
  }
}

main();
