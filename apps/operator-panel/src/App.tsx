import { useEffect, useRef, useState } from 'react';

import {
  type BridgeErrorPayload,
  BridgeError,
  checkPermission,
  createBackup,
  decideApproval,
  dryRunMigration,
  executeApproval,
  exportRunArtifacts,
  exportSupportBundle,
  fetchApprovals,
  getComputerUseSessionState,
  fetchGaReadiness,
  fetchIdentity,
  fetchKeysStatus,
  fetchSecurityBaseline,
  getRunReplay,
  getRunStatus,
  handshake,
  isBridgePreviewMode,
  listRuns,
  pauseComputerUseSession,
  planMigration,
  readArtifact,
  resolveConfig,
  resumeComputerUseSession,
  resumeTeamRun,
  rotateKeyPlan,
  runQualification,
  snapshotMetrics,
  stopComputerUseSession,
  submitComputerUseRun,
  submitTeamRun,
  tailEvents,
  verifyBackup,
  verifyRestore,
  verifySignedArtifact,
  showApproval,
} from './bridge';
import { hasContractMismatch } from './capabilities';
import { ThemeProvider } from './context/ThemeContext';
import { dictionaries } from './i18n';
import { actorForOperator, canMutateWithOperatorId } from './operator';
import {
  type PanelSettings,
  type LocaleMode,
  isOperatorIdValid,
  loadSettings,
  resolveLocale,
  saveSettings,
} from './settings';
import {
  buildWorkspaceSnapshot,
  readWorkspaceProgress,
  type WorkspaceStageKey,
} from './workspace';
import {
  buildActivityItems,
  buildNotificationItems,
  buildPendingApprovalSummaries,
  buildRuntimeSummaryItems,
  buildSessionEventItems,
  buildSystemHealthSummary,
  mapWorkspaceStageToMissionStage,
} from './missionMappers';
import { MissionControlView } from './components/mission/MissionControlView';
import { AppShell } from './components/shell/AppShell';
import { RightRail } from './components/shell/RightRail';
import type { ShellViewKey } from './components/shell/Sidebar';

type ViewKey = 'workspace' | 'tasks' | 'approvals' | 'runs' | 'system' | 'operations' | 'settings';
type RunTabKey = 'overview' | 'stream' | 'approvals' | 'artifacts' | 'replay' | 'diagnostics';
type OperationTabKey = 'identity' | 'qualification' | 'security' | 'keys' | 'support' | 'maintenance';
type AutomationMode = 'assisted' | 'supervised';

type Toast = {
  id: number;
  kind: 'ok' | 'error';
  text: string;
};

type AppContentProps = {
  settings: PanelSettings;
  updateSettings: (next: Partial<PanelSettings>) => void;
};

type TaskFormState = {
  request: string;
  specPath: string;
  caseId: string;
  jobId: string;
  provider: string;
  fallbackProvider: string;
  model: string;
  hfModelId: string;
};

type OperationsFormState = {
  permission: string;
  verifyPath: string;
  supportOutput: string;
  backupOutputDir: string;
  backupVerifyDir: string;
  restoreVerifyDir: string;
  readinessReport: string;
  readinessQualificationReport: string;
  qualificationMode: string;
  qualificationOutputRoot: string;
  qualificationWorkloads: string;
  qualificationMergeFromReport: string;
  qualificationSoakHours: string;
  keyNextKeyId: string;
  keyActivateAt: string;
  keyRetireAfter: string;
};

const ARTIFACT_NAMES = ['status.json', 'tasks.json', 'handoffs.json', 'audit_envelope.json'] as const;
function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readArray(source: Record<string, unknown>, key: string): unknown[] {
  const value = source[key];
  return Array.isArray(value) ? value : [];
}

function readBool(source: Record<string, unknown>, key: string): boolean {
  return source[key] === true;
}

function humanizeCode(value: string): string {
  return value
    .replaceAll('.', ' ')
    .replaceAll('_', ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function extractJobId(payload: unknown): string {
  const record = asRecord(payload);
  return readString(record, 'jobId') || readString(record, 'job_id');
}

function getErrorPayload(error: unknown): BridgeErrorPayload | null {
  if (error instanceof BridgeError) {
    return error.payload;
  }
  return null;
}

function JsonPanel({ value }: { value: unknown }) {
  return <pre className="json-panel">{JSON.stringify(value ?? {}, null, 2)}</pre>;
}

function mergeRunStatusWithSessionState(runStatusPayload: unknown, sessionStatePayload: unknown): unknown {
  const runRecord = asRecord(runStatusPayload);
  const sessionRecord = asRecord(sessionStatePayload);
  const next: Record<string, unknown> = { ...runRecord };
  const sessionJob = asRecord(sessionRecord.job);
  const sessionComputerUse = asRecord(sessionRecord.computer_use);

  if (Object.keys(sessionJob).length > 0) {
    next.job = { ...asRecord(runRecord.job), ...sessionJob };
  }
  if (Object.keys(sessionComputerUse).length > 0) {
    next.computer_use = { ...asRecord(runRecord.computer_use), ...sessionComputerUse };
  }

  return next;
}

function AppContent({ settings, updateSettings }: AppContentProps) {
  const previewMode = isBridgePreviewMode();

  const [activeView, setActiveView] = useState<ViewKey>('workspace');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [runTab, setRunTab] = useState<RunTabKey>('overview');
  const [operationTab, setOperationTab] = useState<OperationTabKey>('identity');
  const [automationMode, setAutomationMode] = useState<AutomationMode>('assisted');
  const [stepMode, setStepMode] = useState(true);
  const [askBeforeExternal, setAskBeforeExternal] = useState(true);
  const [askBeforeDeletion, setAskBeforeDeletion] = useState(true);
  const [askBeforeSend, setAskBeforeSend] = useState(true);

  const [handshakeData, setHandshakeData] = useState<unknown>(null);
  const [configData, setConfigData] = useState<unknown>(null);
  const [handshakeError, setHandshakeError] = useState<BridgeErrorPayload | null>(null);

  const [approvalsData, setApprovalsData] = useState<unknown>({ pending: [] });
  const [selectedApprovalId, setSelectedApprovalId] = useState('');
  const [approvalDetail, setApprovalDetail] = useState<unknown>(null);

  const [runsData, setRunsData] = useState<unknown>({ items: [] });
  const [selectedRunId, setSelectedRunId] = useState('');
  const [runStatus, setRunStatus] = useState<unknown>(null);
  const [computerUseState, setComputerUseState] = useState<unknown>(null);
  const [runReplay, setRunReplay] = useState<unknown>(null);
  const [artifactsByName, setArtifactsByName] = useState<Record<string, unknown>>({});
  const [selectedArtifactName, setSelectedArtifactName] = useState<string>('status.json');
  const [showRawArtifact, setShowRawArtifact] = useState(false);

  const [events, setEvents] = useState<unknown[]>([]);
  const [eventsCursor, setEventsCursor] = useState(0);
  const [eventsWarning, setEventsWarning] = useState('');
  const cursorRef = useRef(0);

  const [taskForm, setTaskForm] = useState<TaskFormState>({
    request: '',
    specPath: '',
    caseId: '',
    jobId: '',
    provider: '',
    fallbackProvider: '',
    model: '',
    hfModelId: '',
  });
  const [resumeForm, setResumeForm] = useState({
    specPath: '',
    resumeJobId: '',
    provider: '',
    fallbackProvider: '',
    model: '',
    hfModelId: '',
  });
  const [operationsForm, setOperationsForm] = useState<OperationsFormState>({
    permission: 'runtime.run',
    verifyPath: '',
    supportOutput: '',
    backupOutputDir: '',
    backupVerifyDir: '',
    restoreVerifyDir: '',
    readinessReport: 'artifacts/ga_readiness_report.json',
    readinessQualificationReport: 'artifacts/qualification_report.json',
    qualificationMode: 'mixed',
    qualificationOutputRoot: 'artifacts/qualification',
    qualificationWorkloads: '',
    qualificationMergeFromReport: '',
    qualificationSoakHours: '6',
    keyNextKeyId: '',
    keyActivateAt: '',
    keyRetireAfter: '',
  });
  const [operationOutputs, setOperationOutputs] = useState<Record<string, unknown>>({});
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [dismissedNotifications, setDismissedNotifications] = useState<string[]>([]);

  const locale = resolveLocale(settings.locale);
  const t = dictionaries[locale];

  const handshakeRecord = asRecord(handshakeData);
  const capabilities = asRecord(handshakeRecord.capabilities);
  const features = asRecord(capabilities.features);
  const doctor = asRecord(handshakeRecord.doctor);
  const supportedProfiles = readArray(capabilities, 'profiles');
  const contractMismatch = hasContractMismatch(handshakeData);
  const operatorIdValid = isOperatorIdValid(settings.operatorId);
  const canMutate = canMutateWithOperatorId(settings.operatorId, contractMismatch);

  const pendingApprovals = readArray(asRecord(approvalsData), 'pending');
  const runItems = readArray(asRecord(runsData), 'items');
  const selectedApproval = asRecord(approvalDetail);
  const runStatusRecord = asRecord(runStatus);
  const runJob = asRecord(runStatusRecord.job);
  const runComputerUse = asRecord(runStatusRecord.computer_use);
  const controlRegistry = asRecord(asRecord(computerUseState).registry);
  const runStatusValue = readString(runJob, 'status');
  const isComputerUseRun =
    Object.keys(runComputerUse).length > 0 || readString(runJob, 'team_id') === 'aegis-computer-use';
  const linkedApprovals = pendingApprovals.filter(
    (item) => readString(asRecord(item), 'run_id') === selectedRunId,
  );
  const driftEvents = events.filter((item) => {
    const name = readString(asRecord(item), 'event').toLowerCase();
    return name.includes('snapshot_drift') || name.includes('approval_stale') || name.includes('stale_');
  });
  const configRecord = asRecord(configData);

  function pushToast(kind: Toast['kind'], text: string) {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, kind, text }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 4200);
  }

  async function refreshHandshake() {
    try {
      const payload = await handshake(settings);
      setHandshakeData(payload);
      setHandshakeError(null);
    } catch (error) {
      setHandshakeError(getErrorPayload(error));
    }
  }

  async function refreshConfig() {
    try {
      const payload = await resolveConfig(settings);
      setConfigData(payload);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function refreshApprovals() {
    try {
      const payload = await fetchApprovals(settings);
      setApprovalsData(payload);
      const pending = readArray(asRecord(payload), 'pending');
      if (!selectedApprovalId && pending.length > 0) {
        setSelectedApprovalId(readString(asRecord(pending[0]), 'approval_id'));
      }
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function refreshRuns() {
    try {
      const payload = await listRuns(settings);
      setRunsData(payload);
      const items = readArray(asRecord(payload), 'items');
      if (!selectedRunId && items.length > 0) {
        setSelectedRunId(readString(asRecord(items[0]), 'job_id'));
      }
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function refreshCore() {
    await Promise.all([refreshHandshake(), refreshConfig(), refreshApprovals(), refreshRuns()]);
  }

  async function loadApprovalDetail(approvalId: string) {
    if (!approvalId) {
      setApprovalDetail(null);
      return;
    }
    try {
      const payload = await showApproval(settings, approvalId);
      setApprovalDetail(payload);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function loadRunContext(runId: string, notifyErrors = true) {
    if (!runId) {
      return;
    }

    try {
      const [statusPayload, replayPayload, sessionStatePayload] = await Promise.all([
        getRunStatus(settings, runId),
        getRunReplay(settings, runId),
        getComputerUseSessionState(settings, runId).catch(() => null),
      ]);
      setRunStatus(mergeRunStatusWithSessionState(statusPayload, sessionStatePayload));
      setComputerUseState(sessionStatePayload);
      setRunReplay(replayPayload);

      const nextArtifacts: Record<string, unknown> = {};
      await Promise.all(
        ARTIFACT_NAMES.map(async (name) => {
          try {
            nextArtifacts[name] = await readArtifact(settings, runId, name);
          } catch {
            nextArtifacts[name] = { artifactName: name, payload: {} };
          }
        }),
      );
      setArtifactsByName(nextArtifacts);
    } catch (error) {
      if (!notifyErrors) {
        return;
      }
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  useEffect(() => {
    void refreshCore();
  }, [settings.mode, settings.cliPath, settings.bundledPythonPath, settings.profile, settings.rootDir]);

  useEffect(() => {
    if (!resumeForm.specPath && taskForm.specPath) {
      setResumeForm((prev) => ({ ...prev, specPath: taskForm.specPath }));
    }
  }, [resumeForm.specPath, taskForm.specPath]);

  useEffect(() => {
    if (!settings.debugRaw) {
      setShowRawArtifact(false);
    }
  }, [settings.debugRaw]);

  useEffect(() => {
    void loadApprovalDetail(selectedApprovalId);
  }, [selectedApprovalId, settings.profile]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    setEvents([]);
    setEventsCursor(0);
    cursorRef.current = 0;
    setEventsWarning('');
    setComputerUseState(null);
    void loadRunContext(selectedRunId);
  }, [selectedRunId, settings.profile, settings.rootDir]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }

    let cancelled = false;
    let timer: number | null = null;

    const poll = async () => {
      if (cancelled) {
        return;
      }

      try {
        const [statusPayload, sessionStatePayload] = await Promise.all([
          getRunStatus(settings, selectedRunId),
          getComputerUseSessionState(settings, selectedRunId).catch(() => null),
        ]);
        setRunStatus(mergeRunStatusWithSessionState(statusPayload, sessionStatePayload));
        setComputerUseState(sessionStatePayload);

        const stream = await tailEvents(settings, selectedRunId, cursorRef.current, 96 * 1024, 200);
        if (stream.reset) {
          setEvents(stream.events);
        } else if (stream.events.length > 0) {
          setEvents((prev) => [...prev, ...stream.events]);
        }

        cursorRef.current = stream.nextCursor;
        setEventsCursor(stream.nextCursor);
        if (stream.badLineCount > 0 || stream.truncated) {
          setEventsWarning(
            `events tail warning: badLineCount=${stream.badLineCount}, truncated=${String(stream.truncated)}`,
          );
        } else {
          setEventsWarning('');
        }

        const liveStatus = readString(asRecord(asRecord(statusPayload).job), 'status');
        const cadence = liveStatus === 'running' ? 1500 : liveStatus === 'blocked' ? 3500 : 6000;
        timer = window.setTimeout(() => {
          void poll();
        }, cadence);
      } catch (error) {
        const parsed = getErrorPayload(error);
        if (parsed) {
          setEventsWarning(`${parsed.code}: ${parsed.message}`);
        }
        timer = window.setTimeout(() => {
          void poll();
        }, 6000);
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [selectedRunId, settings.profile, settings.rootDir]);

  async function onDecideApproval(approve: boolean) {
    if (!selectedApprovalId || !canMutate) {
      pushToast('error', t.setOperatorId);
      return;
    }

    const actor = actorForOperator(settings.operatorId);
    const label = approve ? t.approve : t.reject;
    const confirmed = window.confirm(`${label}\n${selectedApprovalId}\n${actor}`);
    if (!confirmed) {
      return;
    }

    try {
      await decideApproval(settings, selectedApprovalId, approve, settings.operatorId, 'operator workspace action');
      pushToast('ok', `${label} OK`);
      await Promise.all([refreshApprovals(), refreshRuns()]);
      if (selectedRunId) {
        await loadRunContext(selectedRunId, false);
      }
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onExecuteApproval() {
    if (!selectedApprovalId || !canMutate) {
      pushToast('error', t.setOperatorId);
      return;
    }

    const actor = actorForOperator(settings.operatorId);
    const confirmed = window.confirm(`${t.execute}\n${selectedApprovalId}\n${actor}`);
    if (!confirmed) {
      return;
    }

    try {
      await executeApproval(settings, selectedApprovalId, settings.operatorId);
      pushToast('ok', `${t.execute} OK`);
      await Promise.all([refreshApprovals(), refreshRuns()]);
      if (selectedRunId) {
        await loadRunContext(selectedRunId, false);
      }
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onSubmitTask() {
    if (!taskForm.specPath.trim() || !taskForm.request.trim()) {
      pushToast('error', t.submitValidation);
      return;
    }

    try {
      const payload = await submitTeamRun(settings, {
        specPath: taskForm.specPath,
        request: taskForm.request,
        caseId: taskForm.caseId || undefined,
        jobId: taskForm.jobId || undefined,
        provider: taskForm.provider || undefined,
        fallbackProvider: taskForm.fallbackProvider || undefined,
        model: taskForm.model || undefined,
        hfModelId: taskForm.hfModelId || undefined,
      });
      const jobId = extractJobId(payload);
      if (jobId) {
        setSelectedRunId(jobId);
        setRunStatus({ job: { job_id: jobId, status: 'pending' } });
      }
      setActiveView('workspace');
      pushToast('ok', `${t.submitRun} OK`);
      void refreshRuns();
      window.setTimeout(() => {
        void refreshRuns();
      }, 1200);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onSubmitComputerUseSession() {
    if (!taskForm.request.trim()) {
      pushToast('error', t.sessionValidation);
      return;
    }

    const mode: 'dry_run' | 'step_approval' | 'execute' =
      automationMode === 'assisted' || stepMode ? 'step_approval' : 'execute';

    try {
      const payload = await submitComputerUseRun(settings, {
        request: taskForm.request,
        caseId: taskForm.caseId || undefined,
        jobId: taskForm.jobId || undefined,
        mode,
        provider: taskForm.provider || undefined,
        fallbackProvider: taskForm.fallbackProvider || undefined,
        model: taskForm.model || undefined,
        hfModelId: taskForm.hfModelId || undefined,
      });
      const jobId = extractJobId(payload);
      if (jobId) {
        setSelectedRunId(jobId);
        setRunStatus({
          job: {
            job_id: jobId,
            request: taskForm.request,
            status: 'running',
            team_id: 'aegis-computer-use',
          },
          computer_use: {
            mode,
            lifecycle_state: 'running',
            stage: 'plan',
            paused: false,
            stopped: false,
          },
        });
      }
      setActiveView('workspace');
      pushToast('ok', `${t.startSession} OK`);
      void refreshRuns();
      window.setTimeout(() => {
        void refreshRuns();
        if (jobId) {
          void loadRunContext(jobId, false);
        }
      }, 1200);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onResumeRun() {
    if (!selectedRunId || !resumeForm.specPath.trim()) {
      pushToast('error', t.resumeValidation);
      return;
    }

    try {
      const payload = await resumeTeamRun(settings, {
        specPath: resumeForm.specPath,
        sourceJobId: selectedRunId,
        resumeJobId: resumeForm.resumeJobId || undefined,
        provider: resumeForm.provider || undefined,
        fallbackProvider: resumeForm.fallbackProvider || undefined,
        model: resumeForm.model || undefined,
        hfModelId: resumeForm.hfModelId || undefined,
      });
      const jobId = extractJobId(payload);
      if (jobId) {
        setSelectedRunId(jobId);
      }
      pushToast('ok', `${t.resumeRun} OK`);
      void refreshRuns();
      window.setTimeout(() => {
        void refreshRuns();
      }, 1200);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onControlSession(command: 'pause' | 'resume' | 'stop') {
    if (!selectedRunId || !isComputerUseRun) {
      return;
    }

    try {
      const label = command === 'pause' ? t.pause : command === 'resume' ? t.resumeRun : t.stopNow;
      let controlPayload: unknown;
      if (command === 'pause') {
        controlPayload = await pauseComputerUseSession(settings, selectedRunId);
      } else if (command === 'resume') {
        controlPayload = await resumeComputerUseSession(settings, selectedRunId);
      } else {
        const confirmed = window.confirm(`${t.stopNow}\n${selectedRunId}`);
        if (!confirmed) {
          return;
        }
        controlPayload = await stopComputerUseSession(settings, selectedRunId);
      }

      const statePayload = await getComputerUseSessionState(settings, selectedRunId).catch(() => null);
      setComputerUseState(statePayload);
      const controlRecord = asRecord(controlPayload);
      const outcome = readString(controlRecord, 'outcome', 'accepted');
      const reason = readString(controlRecord, 'reason');
      const outcomeLabel = humanizeCode(outcome);
      if (outcome === 'rejected') {
        pushToast('error', `${label}: ${outcomeLabel}${reason ? ` (${humanizeCode(reason)})` : ''}`);
      } else {
        pushToast('ok', `${label}: ${outcomeLabel}${reason ? ` (${humanizeCode(reason)})` : ''}`);
      }
      window.setTimeout(() => {
        void loadRunContext(selectedRunId, false);
        void refreshRuns();
      }, 500);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onExportArtifacts() {
    if (!selectedRunId) {
      return;
    }

    const target = window.prompt(t.exportPrompt, `./exports/${selectedRunId}`);
    if (!target) {
      return;
    }

    try {
      await exportRunArtifacts(settings, selectedRunId, target);
      pushToast('ok', t.exportDone);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onApproveAndContinue() {
    if (!selectedApprovalId || !canMutate) {
      pushToast('error', t.setOperatorId);
      return;
    }

    const actor = actorForOperator(settings.operatorId);
    const confirmed = window.confirm(`Onayla ve Devam Et\n${selectedApprovalId}\n${actor}`);
    if (!confirmed) {
      return;
    }

    try {
      await decideApproval(settings, selectedApprovalId, true, settings.operatorId, 'mission control approval');
      await executeApproval(settings, selectedApprovalId, settings.operatorId);
      pushToast('ok', 'Onay akışı tamamlandı');
      await Promise.all([refreshApprovals(), refreshRuns()]);
      if (selectedRunId) {
        await loadRunContext(selectedRunId, false);
      }
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function runOperation(key: string, task: () => Promise<unknown>) {
    try {
      const payload = await task();
      setOperationOutputs((prev) => ({ ...prev, [key]: payload }));
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        setOperationOutputs((prev) => ({ ...prev, [key]: parsed }));
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  function confirmRawDisclosure(label: string): boolean {
    if (!settings.debugRaw) {
      pushToast('error', 'Ham payload modu ayarlardan açılmalı.');
      return false;
    }
    return window.confirm(`${label}\nHam payload hassas bilgi içerebilir. Devam edilsin mi?`);
  }

  const selectedArtifactPayload = artifactsByName[selectedArtifactName];
  const parsedArtifact = asRecord(selectedArtifactPayload);
  const artifactValue = parsedArtifact.payload;
  const operationOutput = operationOutputs[operationTab] ?? {};
  const workspaceSnapshot = buildWorkspaceSnapshot({
    runStatus,
    sessionState: computerUseState,
    events,
    pendingApprovals,
    linkedApprovals,
    artifactsByName,
  });
  const workspaceProgress = readWorkspaceProgress(workspaceSnapshot);
  const canResumeSession = Boolean(selectedRunId) && isComputerUseRun && workspaceSnapshot.runtimeState.canResume;

  function workspaceStageLabel(stage: WorkspaceStageKey): string {
    return {
      planning: t.stagePlanning,
      reading_screen: t.stageReadingScreen,
      waiting_approval: t.stageWaitingApproval,
      executing: t.stageExecuting,
      verifying: t.stageVerifying,
      blocked: t.stageBlocked,
      done: t.stageDone,
    }[stage];
  }

  function formatTimestamp(value: string, fallback = '-'): string {
    if (!value) {
      return fallback;
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(parsed);
  }

  function formatClock(value: string, fallback: string): string {
    if (!value) {
      return fallback;
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return fallback;
    }
    return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(parsed);
  }

  const selectedRunRecord = asRecord(
    runItems.find((item) => readString(asRecord(item), 'job_id') === selectedRunId),
  );
  const runOptions = runItems
    .map((item) => {
      const row = asRecord(item);
      const id = readString(row, 'job_id');
      return id ? { id, label: id } : null;
    })
    .filter((item): item is { id: string; label: string } => item !== null);
  if (selectedRunId && !runOptions.some((item) => item.id === selectedRunId)) {
    runOptions.unshift({ id: selectedRunId, label: selectedRunId });
  }

  const selectedCreatedAt =
    readString(runJob, 'created_at') ||
    readString(selectedRunRecord, 'created_at') ||
    readString(runJob, 'started_at');
  const startedAt = formatTimestamp(selectedCreatedAt, previewMode ? '14 May 2025 14:32' : '-');
  const duration = readString(runJob, 'duration') || readString(runComputerUse, 'duration') || (previewMode ? '00:03:18' : '-');
  const sessionId =
    readString(controlRegistry, 'session_id') ||
    readString(runComputerUse, 'session_id') ||
    (previewMode ? 'session_7f3a' : '-');
  const missionStatusCode =
    handshakeError?.code ||
    readString(runComputerUse, 'last_error') ||
    (runStatusValue ? humanizeCode(runStatusValue).toUpperCase() : readString(doctor, 'status', 'Bilinmiyor'));
  const missionStatusError =
    handshakeError?.message ||
    workspaceSnapshot.blockedReason ||
    readString(runComputerUse, 'last_error_message') ||
    (previewMode ? 'Hata: No such file or directory (os error 2)' : 'Ölçüm yok');
  const sessionStatus = workspaceSnapshot.currentStatus || runStatusValue || readString(doctor, 'status', 'Bilinmiyor');
  const approvalRows = pendingApprovals.map((item) => asRecord(item));
  const activeApproval =
    approvalRows.find((item) => readString(item, 'approval_id') === selectedApprovalId) ||
    approvalRows[0] ||
    {};
  const activeApprovalId = readString(activeApproval, 'approval_id');
  const hasApproval = Boolean(activeApprovalId);
  const approvalLabel =
    readString(activeApproval, 'summary') ||
    readString(activeApproval, 'target_kind') ||
    'Plan gözden geçir ve çalıştırmaya izin ver.';
  const approvalDisabledReason = contractMismatch
    ? t.contractMismatch
    : !settings.operatorId.trim()
      ? t.setOperatorId
      : !operatorIdValid
        ? 'Operatör ID geçersiz.'
        : !activeApprovalId
          ? 'Seçili onay yok.'
          : '';
  const approvalDisabled = !canMutate || !activeApprovalId;
  const systemHealth = buildSystemHealthSummary({
    coreMode: settings.mode,
    handshakeRecord,
    doctor,
    metricsPayload: operationOutputs.metrics,
  });
  const activityItems = buildActivityItems(workspaceSnapshot, formatClock);
  const sessionEvents = buildSessionEventItems(workspaceSnapshot, formatClock);
  const runtimeSummary = buildRuntimeSummaryItems({
    snapshot: workspaceSnapshot,
    selectedRunId,
    hasApproval,
    stageLabel: workspaceStageLabel(workspaceSnapshot.stage),
    systemHealth,
  });
  const notifications = buildNotificationItems({
    approvalRows,
    timeline: workspaceSnapshot.timeline,
    dismissedIds: dismissedNotifications,
    formatClock,
  });
  const pendingApprovalSummaries = buildPendingApprovalSummaries(approvalRows, selectedRunId);
  const canResumeFromQuickAction =
    canResumeSession || (Boolean(selectedRunId) && Boolean(resumeForm.specPath.trim()));
  const resumeDisabledReason = !selectedRunId
    ? 'Seçili çalıştırma yok.'
    : !canResumeFromQuickAction
      ? 'Devam için görev spec yolu veya resumable oturum gerekli.'
      : '';
  const cancelDisabled = !selectedRunId || !isComputerUseRun || !workspaceSnapshot.runtimeState.canStop;
  const cancelDisabledReason = !selectedRunId
    ? 'Seçili çalıştırma yok.'
    : !isComputerUseRun
      ? 'İptal yalnızca aktif computer-use oturumlarında kullanılabilir.'
      : !workspaceSnapshot.runtimeState.canStop
        ? 'Runtime bu durumda durdurma kabul etmiyor.'
        : '';

  return (
    <AppShell
      activeView={activeView as ShellViewKey}
      mobileNavOpen={mobileNavOpen}
      operatorId={settings.operatorId.trim()}
      previewMode={previewMode}
      operatorWarning={!operatorIdValid ? t.setOperatorId : ''}
      contractWarning={contractMismatch ? t.contractMismatch : ''}
      pendingApprovalCount={pendingApprovals.length}
      warningCount={driftEvents.length}
      toasts={toasts}
      onNavigate={(view) => setActiveView(view)}
      onToggleNav={() => setMobileNavOpen((value) => !value)}
      onCloseNav={() => setMobileNavOpen(false)}
      onRefresh={() => void refreshCore()}
      rightRail={
        <RightRail
          notifications={notifications}
          selectedRunId={selectedRunId || '-'}
          sessionId={sessionId}
          mode={settings.mode === 'auto' ? 'Yardımlı' : settings.mode}
          profile={settings.profile}
          startedAt={startedAt}
          duration={duration}
          systemHealth={systemHealth}
          pendingApprovals={pendingApprovalSummaries}
          resumeDisabled={!canResumeFromQuickAction}
          resumeDisabledReason={resumeDisabledReason}
          terminalDisabled
          terminalDisabledReason="Terminal entegrasyonu bu sürümde bağlı değil."
          exportDisabled={!selectedRunId}
          exportDisabledReason={!selectedRunId ? 'Seçili çalıştırma yok.' : ''}
          cancelDisabled={cancelDisabled}
          cancelDisabledReason={cancelDisabledReason}
          onDismissNotification={(id) => setDismissedNotifications((prev) => [...prev, id])}
          onRefreshContext={() => {
            void refreshCore();
            if (selectedRunId) {
              void loadRunContext(selectedRunId);
            }
          }}
          onResume={() => {
            if (canResumeSession) {
              void onControlSession('resume');
            } else {
              void onResumeRun();
            }
          }}
          onOpenTerminal={() => {
            pushToast('error', 'Terminal entegrasyonu bu sürümde bağlı değil.');
          }}
          onExport={() => void onExportArtifacts()}
          onCancel={() => void onControlSession('stop')}
          onViewDetails={() => setActiveView('runs')}
          onViewApprovals={() => setActiveView('approvals')}
        />
      }
    >
        {contractMismatch ? <div className="error-banner">{t.contractMismatch}</div> : null}
        {handshakeError ? (
          <div className="error-banner">
            <div>{`${handshakeError.code}: ${handshakeError.message}`}</div>
            <small>{handshakeError.command}</small>
          </div>
        ) : null}

        {activeView === 'workspace' ? (
          <MissionControlView
            runOptions={runOptions}
            selectedRunId={selectedRunId}
            sessionId={sessionId}
            sessionStatus={humanizeCode(sessionStatus)}
            objective={workspaceSnapshot.objective || 'Yönetişimli görevi tarif edin.'}
            priority="Yüksek"
            targetType="Yönetişimli Görev"
            statusCode={missionStatusCode}
            statusError={missionStatusError}
            stageLabel={workspaceStageLabel(workspaceSnapshot.stage)}
            stageKey={mapWorkspaceStageToMissionStage(workspaceSnapshot.stage, hasApproval)}
            startedAt={startedAt}
            duration={duration}
            progress={workspaceProgress}
            activityItems={activityItems}
            sessionEvents={sessionEvents}
            runtimeSummary={runtimeSummary}
            rawSummary={{ runStatus, computerUseState, configData, handshakeData }}
            debugRawEnabled={settings.debugRaw}
            hasApproval={hasApproval}
            approvalLabel={approvalLabel}
            approvalDisabled={approvalDisabled}
            approvalDisabledReason={approvalDisabledReason}
            onSelectRun={setSelectedRunId}
            onRawJsonRequested={() => confirmRawDisclosure('Runtime özeti ham JSON')}
            onApprove={() => void onApproveAndContinue()}
            onEditApproval={() => setActiveView('approvals')}
            onReject={() => void onDecideApproval(false)}
          />
        ) : null}

        {activeView === 'tasks' ? (
          <section className="workspace">
            <div className="workspace-header">
              <div>
                <p className="workspace-kicker">{t.tasksKicker}</p>
                <h2>{t.tasks}</h2>
                <p className="workspace-lead">{t.tasksLead}</p>
              </div>
              <div className="workspace-actions">
                <button className="ghost-btn" type="button" onClick={() => void refreshRuns()}>
                  {t.refreshRuns}
                </button>
                <button className="ghost-btn" type="button" onClick={() => void onSubmitComputerUseSession()}>
                  {t.startSession}
                </button>
                <button className="action-btn" type="button" onClick={() => void onSubmitTask()}>
                  {t.submitRun}
                </button>
              </div>
            </div>

            <div className="section-grid two-up">
              <article className="page-card">
                <h3>{t.taskWorkspace}</h3>
                <div className="toolbar-row">
                  <button
                    className={automationMode === 'assisted' ? 'tab-btn tab-btn-active' : 'tab-btn'}
                    type="button"
                    onClick={() => {
                      setAutomationMode('assisted');
                      setStepMode(true);
                    }}
                  >
                    {t.assistedMode}
                  </button>
                  <button
                    className={automationMode === 'supervised' ? 'tab-btn tab-btn-active' : 'tab-btn'}
                    type="button"
                    onClick={() => {
                      setAutomationMode('supervised');
                      setStepMode(false);
                    }}
                  >
                    {t.supervisedMode}
                  </button>
                </div>
                <div className="control-switches">
                  <label className="field field-inline">
                    <span>{t.askBeforeExternalAction}</span>
                    <input
                      type="checkbox"
                      checked={askBeforeExternal}
                      onChange={(event) => setAskBeforeExternal(event.target.checked)}
                    />
                  </label>
                  <label className="field field-inline">
                    <span>{t.askBeforeDeletion}</span>
                    <input
                      type="checkbox"
                      checked={askBeforeDeletion}
                      onChange={(event) => setAskBeforeDeletion(event.target.checked)}
                    />
                  </label>
                  <label className="field field-inline">
                    <span>{t.askBeforeSend}</span>
                    <input
                      type="checkbox"
                      checked={askBeforeSend}
                      onChange={(event) => setAskBeforeSend(event.target.checked)}
                    />
                  </label>
                </div>
                <div className="form-grid">
                  <label className="field">
                    <span>{t.profile}</span>
                    <select value={settings.profile} onChange={(event) => updateSettings({ profile: event.target.value })}>
                      {(supportedProfiles.length > 0 ? supportedProfiles : [settings.profile]).map((item) => (
                        <option value={String(item)} key={String(item)}>
                          {String(item)}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="field field-span">
                    <span>{t.specPath}</span>
                    <input
                      value={taskForm.specPath}
                      onChange={(event) => setTaskForm((prev) => ({ ...prev, specPath: event.target.value }))}
                      placeholder="examples/team/restricted_pilot.yaml"
                    />
                  </label>

                  <label className="field field-span">
                    <span>{t.request}</span>
                    <textarea
                      rows={6}
                      value={taskForm.request}
                      onChange={(event) => setTaskForm((prev) => ({ ...prev, request: event.target.value }))}
                      placeholder={t.requestPlaceholder}
                    />
                  </label>
                </div>

                <details className="details-panel">
                  <summary>{t.advancedOptions}</summary>
                  <div className="form-grid compact-grid">
                    <label className="field">
                      <span>{t.caseId}</span>
                      <input
                        value={taskForm.caseId}
                        onChange={(event) => setTaskForm((prev) => ({ ...prev, caseId: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.jobId}</span>
                      <input
                        value={taskForm.jobId}
                        onChange={(event) => setTaskForm((prev) => ({ ...prev, jobId: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.provider}</span>
                      <input
                        value={taskForm.provider}
                        onChange={(event) => setTaskForm((prev) => ({ ...prev, provider: event.target.value }))}
                        placeholder="auto"
                      />
                    </label>
                    <label className="field">
                      <span>{t.fallbackProvider}</span>
                      <input
                        value={taskForm.fallbackProvider}
                        onChange={(event) =>
                          setTaskForm((prev) => ({ ...prev, fallbackProvider: event.target.value }))
                        }
                        placeholder="transformers"
                      />
                    </label>
                    <label className="field">
                      <span>{t.model}</span>
                      <input
                        value={taskForm.model}
                        onChange={(event) => setTaskForm((prev) => ({ ...prev, model: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.hfModelId}</span>
                      <input
                        value={taskForm.hfModelId}
                        onChange={(event) => setTaskForm((prev) => ({ ...prev, hfModelId: event.target.value }))}
                      />
                    </label>
                  </div>
                </details>
              </article>

              <article className="page-card">
                <h3>{t.submitReadiness}</h3>
                <div className="metric-list">
                  <div className="metric-row">
                    <span>{t.operatorId}</span>
                    <strong>{settings.operatorId.trim() || '-'}</strong>
                  </div>
                  <div className="metric-row">
                    <span>{t.rootDir}</span>
                    <strong>{settings.rootDir}</strong>
                  </div>
                  <div className="metric-row">
                    <span>{t.profile}</span>
                    <strong>{settings.profile}</strong>
                  </div>
                  <div className="metric-row">
                    <span>{t.workflowParity}</span>
                    <strong>{readBool(features, 'operatorWorkflowParity') ? t.enabled : t.disabled}</strong>
                  </div>
                </div>
                <div className="stack-actions">
                  <button className="action-btn" type="button" onClick={() => void onSubmitTask()}>
                    {t.submitRun}
                  </button>
                  <button
                    className="ghost-btn"
                    type="button"
                    onClick={() => {
                      setActiveView('runs');
                    }}
                  >
                    {t.openRuns}
                  </button>
                </div>
              </article>
            </div>
          </section>
        ) : null}

        {activeView === 'approvals' ? (
          <section className="workspace">
            <div className="workspace-header">
              <div>
                <p className="workspace-kicker">{t.approvalsKicker}</p>
                <h2>{t.approvals}</h2>
                <p className="workspace-lead">{t.approvalsLead}</p>
              </div>
              <div className="workspace-actions">
                <button className="ghost-btn" type="button" onClick={() => void refreshApprovals()}>
                  {t.refresh}
                </button>
                <button className="action-btn" type="button" disabled={!canMutate || !selectedApprovalId} onClick={() => void onDecideApproval(true)}>
                  {t.approve}
                </button>
                <button className="ghost-btn" type="button" disabled={!canMutate || !selectedApprovalId} onClick={() => void onDecideApproval(false)}>
                  {t.reject}
                </button>
                <button className="action-btn action-danger" type="button" disabled={!canMutate || !selectedApprovalId} onClick={() => void onExecuteApproval()}>
                  {t.execute}
                </button>
              </div>
            </div>

            <div className="section-grid approval-grid">
              <article className="page-card">
                <h3>{t.pendingApprovals}</h3>
                <div className="list-scroll">
                  {pendingApprovals.length === 0 ? <p className="supporting">{t.noData}</p> : null}
                  {pendingApprovals.map((item) => {
                    const row = asRecord(item);
                    const approvalId = readString(row, 'approval_id');
                    return (
                      <button
                        key={approvalId}
                        type="button"
                        className={approvalId === selectedApprovalId ? 'list-row list-row-active' : 'list-row'}
                        onClick={() => setSelectedApprovalId(approvalId)}
                      >
                        <strong>{approvalId}</strong>
                        <span>{readString(row, 'target_kind')}</span>
                        <small>{readString(row, 'status')}</small>
                      </button>
                    );
                  })}
                </div>
              </article>

              <article className="page-card">
                <h3>{t.selectedApproval}</h3>
                {selectedApprovalId ? <JsonPanel value={selectedApproval} /> : <p className="supporting">{t.noSelection}</p>}
              </article>
            </div>
          </section>
        ) : null}

        {activeView === 'runs' ? (
          <section className="workspace">
            <div className="workspace-header">
              <div>
                <p className="workspace-kicker">{t.runsKicker}</p>
                <h2>{t.runs}</h2>
                <p className="workspace-lead">{t.runsLead}</p>
              </div>
              <div className="workspace-actions">
                <button className="ghost-btn" type="button" onClick={() => void refreshRuns()}>
                  {t.refreshRuns}
                </button>
                <button className="ghost-btn" type="button" disabled={!selectedRunId} onClick={() => void loadRunContext(selectedRunId)}>
                  {t.refreshContext}
                </button>
                <button className="action-btn" type="button" disabled={!selectedRunId} onClick={() => void onExportArtifacts()}>
                  {t.export}
                </button>
              </div>
            </div>

            {driftEvents.length > 0 ? <div className="warning-banner">{t.driftWarning}</div> : null}

            <div className="section-grid runs-grid">
              <article className="page-card">
                <h3>{t.recentRuns}</h3>
                <div className="list-scroll">
                  {runItems.length === 0 ? <p className="supporting">{t.noData}</p> : null}
                  {runItems.map((item) => {
                    const row = asRecord(item);
                    const jobId = readString(row, 'job_id');
                    return (
                      <button
                        key={jobId}
                        type="button"
                        className={jobId === selectedRunId ? 'list-row list-row-active' : 'list-row'}
                        onClick={() => setSelectedRunId(jobId)}
                      >
                        <strong>{jobId}</strong>
                        <span>{readString(row, 'status')}</span>
                        <small>{readString(row, 'created_at')}</small>
                      </button>
                    );
                  })}
                </div>
              </article>

              <article className="page-card">
                <div className="tab-strip">
                  {(['overview', 'stream', 'approvals', 'artifacts', 'replay', 'diagnostics'] as RunTabKey[]).map((tab) => (
                    <button
                      key={tab}
                      type="button"
                      className={runTab === tab ? 'tab-btn tab-btn-active' : 'tab-btn'}
                      onClick={() => setRunTab(tab)}
                    >
                      {tab === 'overview'
                        ? t.overview
                        : tab === 'stream'
                          ? t.stream
                          : tab === 'approvals'
                            ? t.approvals
                            : tab === 'artifacts'
                              ? t.artifacts
                              : tab === 'replay'
                                ? t.replay
                                : t.diagnostics}
                    </button>
                  ))}
                </div>

                {!selectedRunId ? <p className="supporting">{t.selectRun}</p> : null}
                {selectedRunId && runTab === 'overview' ? <JsonPanel value={runStatus} /> : null}

                {selectedRunId && runTab === 'stream' ? (
                  <div className="timeline-panel">
                    {eventsWarning ? <div className="warning-inline">{eventsWarning}</div> : null}
                    {events.length === 0 ? <p className="supporting">{t.noData}</p> : null}
                    {events.map((item, index) => {
                      const row = asRecord(item);
                      return (
                        <div className="timeline-event" key={`${index}-${readString(row, 'timestamp', String(index))}`}>
                          <strong>{readString(row, 'event', 'event')}</strong>
                          <span>{readString(row, 'timestamp')}</span>
                          <code>{JSON.stringify(row.data ?? {}, null, 2)}</code>
                        </div>
                      );
                    })}
                  </div>
                ) : null}

                {selectedRunId && runTab === 'approvals' ? (
                  linkedApprovals.length > 0 ? (
                    <JsonPanel value={linkedApprovals} />
                  ) : (
                    <p className="supporting">{t.noLinkedApprovals}</p>
                  )
                ) : null}

                {selectedRunId && runTab === 'artifacts' ? (
                  <div className="artifact-panel">
                    <div className="toolbar-row">
                      <select value={selectedArtifactName} onChange={(event) => setSelectedArtifactName(event.target.value)}>
                        {ARTIFACT_NAMES.map((name) => (
                          <option value={name} key={name}>
                            {name}
                          </option>
                        ))}
                      </select>
                      <button
                        className="ghost-btn"
                        type="button"
                        disabled={!settings.debugRaw}
                        title={settings.debugRaw ? undefined : 'Ham payload modu ayarlardan açılmalı.'}
                        onClick={() => {
                          if (showRawArtifact) {
                            setShowRawArtifact(false);
                            return;
                          }
                          if (confirmRawDisclosure(`${selectedArtifactName} ham JSON`)) {
                            setShowRawArtifact(true);
                          }
                        }}
                      >
                        {showRawArtifact ? t.hideRaw : t.showRaw}
                      </button>
                    </div>
                    <JsonPanel value={showRawArtifact ? parsedArtifact : artifactValue} />
                  </div>
                ) : null}

                {selectedRunId && runTab === 'replay' ? <JsonPanel value={runReplay} /> : null}

                {selectedRunId && runTab === 'diagnostics' ? (
                  <div className="section-grid">
                    <article className="inner-card">
                      <h3>{t.driftSignals}</h3>
                      {driftEvents.length > 0 ? <JsonPanel value={driftEvents} /> : <p className="supporting">{t.noDrift}</p>}
                    </article>
                    <article className="inner-card">
                      <h3>{t.systemContext}</h3>
                      <JsonPanel value={{ doctor: handshakeRecord.doctor ?? {}, config: configData ?? {} }} />
                    </article>
                  </div>
                ) : null}
              </article>
            </div>
          </section>
        ) : null}

        {activeView === 'system' ? (
          <section className="workspace">
            <div className="workspace-header">
              <div>
                <p className="workspace-kicker">{t.systemKicker}</p>
                <h2>{t.system}</h2>
                <p className="workspace-lead">{t.systemLead}</p>
              </div>
              <div className="workspace-actions">
                <button className="ghost-btn" type="button" onClick={() => void refreshHandshake()}>
                  {t.refreshDoctor}
                </button>
                <button className="ghost-btn" type="button" onClick={() => void refreshConfig()}>
                  {t.refreshConfig}
                </button>
              </div>
            </div>

            <div className="metric-grid">
              <article className="metric-card">
                <h3>{t.contractVersion}</h3>
                <p className="metric">{readString(handshakeRecord, 'contractVersion', '-')}</p>
              </article>
              <article className="metric-card">
                <h3>{t.coreVersion}</h3>
                <p className="metric">{readString(handshakeRecord, 'coreVersion', '-')}</p>
              </article>
              <article className="metric-card">
                <h3>{t.profile}</h3>
                <p className="metric">{settings.profile}</p>
              </article>
              <article className="metric-card">
                <h3>{t.runtimeHealth}</h3>
                <p className="metric">{readString(doctor, 'status', '-')}</p>
              </article>
              <article className="metric-card">
                <h3>{t.live}</h3>
                <p className="metric">{eventsCursor}</p>
              </article>
            </div>

            <div className="section-grid two-up">
              <article className="page-card">
                <h3>{t.doctor}</h3>
                <JsonPanel value={doctor} />
              </article>
              <article className="page-card">
                <h3>{t.effectiveConfig}</h3>
                <JsonPanel value={configRecord} />
              </article>
              <article className="page-card">
                <h3>{t.capabilities}</h3>
                <JsonPanel value={capabilities} />
              </article>
              <article className="page-card">
                <h3>{t.capabilityContract}</h3>
                <JsonPanel value={{ profiles: supportedProfiles, features }} />
              </article>
            </div>
          </section>
        ) : null}

        {activeView === 'operations' ? (
          <section className="workspace">
            <div className="workspace-header">
              <div>
                <p className="workspace-kicker">{t.operationsKicker}</p>
                <h2>{t.operations}</h2>
                <p className="workspace-lead">{t.operationsLead}</p>
              </div>
              <div className="workspace-actions">
                <button className="ghost-btn" type="button" onClick={() => void snapshotMetrics(settings).then((payload) => setOperationOutputs((prev) => ({ ...prev, metrics: payload }))).catch(() => undefined)}>
                  {t.quickMetrics}
                </button>
              </div>
            </div>

            <div className="tab-strip">
              {(['identity', 'qualification', 'security', 'keys', 'support', 'maintenance'] as OperationTabKey[]).map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className={operationTab === tab ? 'tab-btn tab-btn-active' : 'tab-btn'}
                  onClick={() => setOperationTab(tab)}
                >
                  {tab === 'identity'
                    ? t.identity
                    : tab === 'qualification'
                      ? t.qualification
                      : tab === 'security'
                        ? t.security
                        : tab === 'keys'
                          ? t.keys
                          : tab === 'support'
                            ? t.support
                            : t.maintenance}
                </button>
              ))}
            </div>

            {operationTab === 'identity' ? (
              <div className="section-grid two-up">
                <article className="page-card">
                  <h3>{t.identity}</h3>
                  <div className="stack-actions">
                    <button className="action-btn" type="button" onClick={() => void runOperation('identity', () => fetchIdentity(settings))}>
                      {t.whoAmI}
                    </button>
                  </div>
                  <label className="field">
                    <span>{t.permission}</span>
                    <input
                      value={operationsForm.permission}
                      onChange={(event) => setOperationsForm((prev) => ({ ...prev, permission: event.target.value }))}
                    />
                  </label>
                  <button
                    className="ghost-btn"
                    type="button"
                    onClick={() => void runOperation('identity', () => checkPermission(settings, operationsForm.permission))}
                  >
                    {t.checkPermission}
                  </button>
                </article>
                <article className="page-card">
                  <h3>{t.operationOutput}</h3>
                  <JsonPanel value={operationOutputs.identity ?? {}} />
                </article>
              </div>
            ) : null}

            {operationTab === 'qualification' ? (
              <div className="section-grid two-up">
                <article className="page-card">
                  <h3>{t.qualification}</h3>
                  <div className="form-grid compact-grid">
                    <label className="field">
                      <span>{t.mode}</span>
                      <input
                        value={operationsForm.qualificationMode}
                        onChange={(event) =>
                          setOperationsForm((prev) => ({ ...prev, qualificationMode: event.target.value }))
                        }
                      />
                    </label>
                    <label className="field">
                      <span>{t.soakHours}</span>
                      <input
                        value={operationsForm.qualificationSoakHours}
                        onChange={(event) =>
                          setOperationsForm((prev) => ({ ...prev, qualificationSoakHours: event.target.value }))
                        }
                      />
                    </label>
                    <label className="field field-span">
                      <span>{t.outputRoot}</span>
                      <input
                        value={operationsForm.qualificationOutputRoot}
                        onChange={(event) =>
                          setOperationsForm((prev) => ({ ...prev, qualificationOutputRoot: event.target.value }))
                        }
                      />
                    </label>
                    <label className="field field-span">
                      <span>{t.workloads}</span>
                      <input
                        value={operationsForm.qualificationWorkloads}
                        onChange={(event) =>
                          setOperationsForm((prev) => ({ ...prev, qualificationWorkloads: event.target.value }))
                        }
                      />
                    </label>
                  </div>
                  <div className="toolbar-row">
                    <button className="action-btn" type="button" onClick={() => void runOperation('qualification', () => snapshotMetrics(settings))}>
                      {t.metricsSnapshot}
                    </button>
                    <button
                      className="ghost-btn"
                      type="button"
                      onClick={() =>
                        void runOperation('qualification', () =>
                          fetchGaReadiness(settings, {
                            report: operationsForm.readinessReport,
                            qualificationReport: operationsForm.readinessQualificationReport,
                          }),
                        )
                      }
                    >
                      {t.gaReadiness}
                    </button>
                    <button
                      className="action-btn"
                      type="button"
                      onClick={() =>
                        void runOperation('qualification', () =>
                          runQualification(settings, {
                            mode: operationsForm.qualificationMode,
                            soakHours: Number(operationsForm.qualificationSoakHours) || 6,
                            outputRoot: operationsForm.qualificationOutputRoot,
                            workloads: operationsForm.qualificationWorkloads || undefined,
                            mergeFromReport: operationsForm.qualificationMergeFromReport || undefined,
                          }),
                        )
                      }
                    >
                      {t.runQualification}
                    </button>
                  </div>
                </article>
                <article className="page-card">
                  <h3>{t.operationOutput}</h3>
                  <JsonPanel value={operationOutput} />
                </article>
              </div>
            ) : null}

            {operationTab === 'security' ? (
              <div className="section-grid two-up">
                <article className="page-card">
                  <h3>{t.security}</h3>
                  <button className="action-btn" type="button" onClick={() => void runOperation('security', () => fetchSecurityBaseline(settings))}>
                    {t.securityBaseline}
                  </button>
                </article>
                <article className="page-card">
                  <h3>{t.operationOutput}</h3>
                  <JsonPanel value={operationOutput} />
                </article>
              </div>
            ) : null}

            {operationTab === 'keys' ? (
              <div className="section-grid two-up">
                <article className="page-card">
                  <h3>{t.keys}</h3>
                  <label className="field">
                    <span>{t.verifyPath}</span>
                    <input
                      value={operationsForm.verifyPath}
                      onChange={(event) => setOperationsForm((prev) => ({ ...prev, verifyPath: event.target.value }))}
                    />
                  </label>
                  <div className="form-grid compact-grid">
                    <label className="field">
                      <span>{t.nextKeyId}</span>
                      <input
                        value={operationsForm.keyNextKeyId}
                        onChange={(event) => setOperationsForm((prev) => ({ ...prev, keyNextKeyId: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.activateAt}</span>
                      <input
                        value={operationsForm.keyActivateAt}
                        onChange={(event) => setOperationsForm((prev) => ({ ...prev, keyActivateAt: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.retireAfter}</span>
                      <input
                        value={operationsForm.keyRetireAfter}
                        onChange={(event) => setOperationsForm((prev) => ({ ...prev, keyRetireAfter: event.target.value }))}
                      />
                    </label>
                  </div>
                  <div className="toolbar-row">
                    <button className="action-btn" type="button" onClick={() => void runOperation('keys', () => fetchKeysStatus(settings))}>
                      {t.keysStatus}
                    </button>
                    <button
                      className="ghost-btn"
                      type="button"
                      onClick={() => void runOperation('keys', () => verifySignedArtifact(settings, operationsForm.verifyPath))}
                    >
                      {t.verifyArtifact}
                    </button>
                    <button
                      className="ghost-btn"
                      type="button"
                      onClick={() =>
                        void runOperation('keys', () =>
                          rotateKeyPlan(settings, {
                            nextKeyId: operationsForm.keyNextKeyId || undefined,
                            activateAt: operationsForm.keyActivateAt || undefined,
                            retireAfter: operationsForm.keyRetireAfter || undefined,
                          }),
                        )
                      }
                    >
                      {t.rotatePlan}
                    </button>
                  </div>
                </article>
                <article className="page-card">
                  <h3>{t.operationOutput}</h3>
                  <JsonPanel value={operationOutput} />
                </article>
              </div>
            ) : null}

            {operationTab === 'support' ? (
              <div className="section-grid two-up">
                <article className="page-card">
                  <h3>{t.support}</h3>
                  <label className="field">
                    <span>{t.outputPathOptional}</span>
                    <input
                      value={operationsForm.supportOutput}
                      onChange={(event) => setOperationsForm((prev) => ({ ...prev, supportOutput: event.target.value }))}
                    />
                  </label>
                  <button
                    className="action-btn"
                    type="button"
                    onClick={() => void runOperation('support', () => exportSupportBundle(settings, operationsForm.supportOutput || undefined))}
                  >
                    {t.exportSupportBundle}
                  </button>
                </article>
                <article className="page-card">
                  <h3>{t.operationOutput}</h3>
                  <JsonPanel value={operationOutput} />
                </article>
              </div>
            ) : null}

            {operationTab === 'maintenance' ? (
              <div className="section-grid two-up">
                <article className="page-card">
                  <h3>{t.maintenance}</h3>
                  <div className="form-grid compact-grid">
                    <label className="field">
                      <span>{t.outputDirOptional}</span>
                      <input
                        value={operationsForm.backupOutputDir}
                        onChange={(event) => setOperationsForm((prev) => ({ ...prev, backupOutputDir: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.backupDir}</span>
                      <input
                        value={operationsForm.backupVerifyDir}
                        onChange={(event) => setOperationsForm((prev) => ({ ...prev, backupVerifyDir: event.target.value }))}
                      />
                    </label>
                    <label className="field">
                      <span>{t.restoreBackupDir}</span>
                      <input
                        value={operationsForm.restoreVerifyDir}
                        onChange={(event) => setOperationsForm((prev) => ({ ...prev, restoreVerifyDir: event.target.value }))}
                      />
                    </label>
                  </div>
                  <div className="toolbar-row">
                    <button
                      className="action-btn"
                      type="button"
                      onClick={() => void runOperation('maintenance', () => createBackup(settings, operationsForm.backupOutputDir || undefined))}
                    >
                      {t.createBackup}
                    </button>
                    <button
                      className="ghost-btn"
                      type="button"
                      onClick={() => void runOperation('maintenance', () => verifyBackup(settings, operationsForm.backupVerifyDir))}
                    >
                      {t.verifyBackup}
                    </button>
                    <button
                      className="ghost-btn"
                      type="button"
                      onClick={() => void runOperation('maintenance', () => verifyRestore(settings, operationsForm.restoreVerifyDir))}
                    >
                      {t.verifyRestore}
                    </button>
                    <button className="ghost-btn" type="button" onClick={() => void runOperation('maintenance', () => planMigration(settings))}>
                      {t.migratePlan}
                    </button>
                    <button className="ghost-btn" type="button" onClick={() => void runOperation('maintenance', () => dryRunMigration(settings))}>
                      {t.migrateDryRun}
                    </button>
                  </div>
                </article>
                <article className="page-card">
                  <h3>{t.operationOutput}</h3>
                  <JsonPanel value={operationOutput} />
                </article>
              </div>
            ) : null}
          </section>
        ) : null}

        {activeView === 'settings' ? (
          <section className="workspace">
            <div className="workspace-header">
              <div>
                <p className="workspace-kicker">{t.settingsKicker}</p>
                <h2>{t.settings}</h2>
                <p className="workspace-lead">{t.settingsLead}</p>
              </div>
            </div>

            <div className="section-grid two-up">
              <article className="page-card">
                <h3>{t.runtimeSection}</h3>
                <div className="form-grid">
                  <label className="field">
                    <span>{t.operatorId}</span>
                    <input
                      value={settings.operatorId}
                      onChange={(event) => updateSettings({ operatorId: event.target.value })}
                      placeholder={t.operatorIdPlaceholder}
                    />
                  </label>
                  <label className="field">
                    <span>{t.rootDir}</span>
                    <input value={settings.rootDir} onChange={(event) => updateSettings({ rootDir: event.target.value })} />
                  </label>
                  <label className="field">
                    <span>{t.mode}</span>
                    <select value={settings.mode} onChange={(event) => updateSettings({ mode: event.target.value as PanelSettings['mode'] })}>
                      <option value="auto">auto</option>
                      <option value="external">external</option>
                      <option value="bundled">bundled</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>{t.cliPath}</span>
                    <input value={settings.cliPath} onChange={(event) => updateSettings({ cliPath: event.target.value })} />
                  </label>
                  <label className="field field-span">
                    <span>{t.bundledPythonPath}</span>
                    <input
                      value={settings.bundledPythonPath}
                      onChange={(event) => updateSettings({ bundledPythonPath: event.target.value })}
                    />
                  </label>
                </div>
              </article>

              <article className="page-card">
                <h3>{t.interfaceSection}</h3>
                <div className="form-grid">
                  <label className="field">
                    <span>{t.locale}</span>
                    <select value={settings.locale} onChange={(event) => updateSettings({ locale: event.target.value as LocaleMode })}>
                      <option value="auto">auto</option>
                      <option value="en">English</option>
                      <option value="tr">Türkçe</option>
                    </select>
                  </label>
                  <label className="field">
                    <span>{t.updaterMode}</span>
                    <select
                      value={settings.updaterMode}
                      onChange={(event) => updateSettings({ updaterMode: event.target.value as PanelSettings['updaterMode'] })}
                    >
                      <option value="off">off</option>
                      <option value="manual">manual</option>
                      <option value="auto">auto</option>
                    </select>
                  </label>
                  <label className="field field-inline">
                    <span>{t.remoteTelemetry}</span>
                    <input
                      type="checkbox"
                      checked={settings.remoteTelemetry}
                      onChange={(event) => updateSettings({ remoteTelemetry: event.target.checked })}
                    />
                  </label>
                  <label className="field field-inline">
                    <span>{t.debugRaw}</span>
                    <input
                      type="checkbox"
                      checked={settings.debugRaw}
                      onChange={(event) => updateSettings({ debugRaw: event.target.checked })}
                    />
                  </label>
                </div>
                <div className="stack-actions">
                  <button
                    className="action-btn"
                    type="button"
                    onClick={() => {
                      saveSettings(settings);
                      pushToast('ok', t.saved);
                    }}
                  >
                    {t.save}
                  </button>
                </div>
              </article>
            </div>
          </section>
        ) : null}
    </AppShell>
  );
}

function App() {
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());

  function updateSettings(next: Partial<PanelSettings>) {
    setSettings((prev) => {
      const merged = { ...prev, ...next };
      saveSettings(merged);
      return merged;
    });
  }

  return (
    <ThemeProvider mode={settings.theme}>
      <AppContent settings={settings} updateSettings={updateSettings} />
    </ThemeProvider>
  );
}

export default App;
