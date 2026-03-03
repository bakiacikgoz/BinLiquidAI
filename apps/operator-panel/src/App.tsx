import { useEffect, useMemo, useRef, useState } from 'react';

import {
  type BridgeErrorPayload,
  BridgeError,
  decideApproval,
  executeApproval,
  exportRunArtifacts,
  fetchApprovals,
  getRunReplay,
  getRunStatus,
  handshake,
  listRuns,
  readArtifact,
  showApproval,
  tailEvents,
} from './bridge';
import { hasContractMismatch } from './capabilities';
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

type ViewKey = 'dashboard' | 'approvals' | 'runs' | 'diagnostics' | 'settings';
type RunTabKey = 'overview' | 'timeline' | 'artifacts' | 'replay';

type Toast = {
  id: number;
  kind: 'ok' | 'error';
  text: string;
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

function getErrorPayload(error: unknown): BridgeErrorPayload | null {
  if (error instanceof BridgeError) {
    return error.payload;
  }
  return null;
}

function App() {
  const [settings, setSettings] = useState<PanelSettings>(() => loadSettings());
  const [activeView, setActiveView] = useState<ViewKey>('dashboard');
  const [runTab, setRunTab] = useState<RunTabKey>('overview');

  const [handshakeData, setHandshakeData] = useState<unknown>(null);
  const [handshakeError, setHandshakeError] = useState<BridgeErrorPayload | null>(null);

  const [approvalsData, setApprovalsData] = useState<unknown>({ pending: [] });
  const [selectedApprovalId, setSelectedApprovalId] = useState<string>('');
  const [approvalDetail, setApprovalDetail] = useState<unknown>(null);

  const [runsData, setRunsData] = useState<unknown>({ items: [] });
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [runStatus, setRunStatus] = useState<unknown>(null);
  const [runReplay, setRunReplay] = useState<unknown>(null);
  const [artifactsByName, setArtifactsByName] = useState<Record<string, unknown>>({});
  const [selectedArtifactName, setSelectedArtifactName] = useState<string>('status.json');

  const [events, setEvents] = useState<unknown[]>([]);
  const [eventsCursor, setEventsCursor] = useState<number>(0);
  const [eventsWarning, setEventsWarning] = useState<string>('');
  const cursorRef = useRef<number>(0);

  const [showRawArtifact, setShowRawArtifact] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const locale = resolveLocale(settings.locale);
  const t = dictionaries[locale];

  const handshakeRecord = asRecord(handshakeData);
  const capabilities = asRecord(handshakeRecord.capabilities);

  const contractMismatch = useMemo(() => hasContractMismatch(handshakeData), [handshakeData]);

  const operatorIdValid = isOperatorIdValid(settings.operatorId);
  const canMutate = canMutateWithOperatorId(settings.operatorId, contractMismatch);

  const pendingApprovals = readArray(asRecord(approvalsData), 'pending');
  const runItems = readArray(asRecord(runsData), 'items');

  function pushToast(kind: Toast['kind'], text: string) {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, kind, text }]);
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((item) => item.id !== id));
    }, 4200);
  }

  function updateSettings(next: Partial<PanelSettings>) {
    setSettings((prev) => {
      const merged = { ...prev, ...next };
      saveSettings(merged);
      return merged;
    });
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

  async function refreshApprovals() {
    try {
      const payload = await fetchApprovals(settings);
      setApprovalsData(payload);
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
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
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

  async function loadRunContext(runId: string) {
    if (!runId) {
      return;
    }
    try {
      const [status, replay] = await Promise.all([
        getRunStatus(settings, runId),
        getRunReplay(settings, runId),
      ]);
      setRunStatus(status);
      setRunReplay(replay);

      const artifactReads = await Promise.all(
        ARTIFACT_NAMES.map(async (name) => {
          const payload = await readArtifact(settings, runId, name);
          return [name, payload] as const;
        }),
      );

      const nextArtifacts: Record<string, unknown> = {};
      for (const [name, payload] of artifactReads) {
        nextArtifacts[name] = payload;
      }
      setArtifactsByName(nextArtifacts);
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  useEffect(() => {
    void refreshHandshake();
    void refreshApprovals();
    void refreshRuns();
  }, [settings.mode, settings.cliPath, settings.bundledPythonPath, settings.profile, settings.rootDir]);

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
        const statusPayload = await getRunStatus(settings, selectedRunId);
        setRunStatus(statusPayload);

        const statusJob = asRecord(asRecord(statusPayload).job);
        const runStatusValue = readString(statusJob, 'status');
        const cadence = runStatusValue === 'running' ? 1500 : runStatusValue === 'blocked' ? 3500 : 6000;

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

  async function onApprove(approve: boolean) {
    if (!selectedApprovalId) {
      return;
    }
    if (!canMutate) {
      pushToast('error', t.setOperatorId);
      return;
    }

    const action = approve ? t.approve : t.reject;
    const actor = actorForOperator(settings.operatorId);
    const confirmed = window.confirm(`${action}\napproval: ${selectedApprovalId}\nactor: ${actor}`);
    if (!confirmed) {
      return;
    }

    try {
      await decideApproval(settings, selectedApprovalId, approve, settings.operatorId, 'operator panel action');
      pushToast('ok', `${action} OK`);
      await refreshApprovals();
      await refreshRuns();
      if (selectedRunId) {
        await loadRunContext(selectedRunId);
      }
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  async function onExecute() {
    if (!selectedApprovalId) {
      return;
    }
    if (!canMutate) {
      pushToast('error', t.setOperatorId);
      return;
    }

    const actor = actorForOperator(settings.operatorId);
    const confirmed = window.confirm(`${t.execute}\napproval: ${selectedApprovalId}\nactor: ${actor}`);
    if (!confirmed) {
      return;
    }

    try {
      await executeApproval(settings, selectedApprovalId, settings.operatorId);
      pushToast('ok', `${t.execute} OK`);
      await refreshApprovals();
      await refreshRuns();
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
    const defaultPath = `./exports/${selectedRunId}`;
    const target = window.prompt('Export directory', defaultPath);
    if (!target) {
      return;
    }

    try {
      await exportRunArtifacts(settings, selectedRunId, target);
      pushToast('ok', 'Export completed');
    } catch (error) {
      const parsed = getErrorPayload(error);
      if (parsed) {
        pushToast('error', `${parsed.code}: ${parsed.message}`);
      }
    }
  }

  const runStatusRecord = asRecord(runStatus);
  const runJob = asRecord(runStatusRecord.job);
  const runStatusValue = readString(runJob, 'status', '');

  const topPill =
    runStatusValue === 'running'
      ? t.working
      : runStatusValue === 'blocked'
        ? t.blockedApproval
        : runStatusValue
          ? t.idle
          : t.statusUnknown;

  const selectedApproval = asRecord(approvalDetail);

  const selectedArtifactPayload = artifactsByName[selectedArtifactName];
  const parsedArtifact = asRecord(selectedArtifactPayload);
  const artifactValue = parsedArtifact.payload;

  const views: Array<{ key: ViewKey; label: string }> = [
    { key: 'dashboard', label: t.dashboard },
    { key: 'approvals', label: t.approvals },
    { key: 'runs', label: t.runs },
    { key: 'diagnostics', label: t.diagnostics },
    { key: 'settings', label: t.settings },
  ];

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-chip">v0.5 beta</div>
          <h1>{t.appTitle}</h1>
          <p>{t.appSubtitle}</p>
        </div>

        <nav className="nav-list">
          {views.map((view) => (
            <button
              key={view.key}
              className={view.key === activeView ? 'nav-item nav-item-active' : 'nav-item'}
              onClick={() => setActiveView(view.key)}
              type="button"
            >
              {view.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <span>{t.operatorId}</span>
          <strong>{settings.operatorId.trim() || '-'}</strong>
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div className="status-strip">
            <span className="pill">{topPill}</span>
            <span className="pill pill-muted">{t.live}: {eventsCursor}</span>
            <button className="ghost-btn" type="button" onClick={() => void refreshHandshake()}>
              {t.refresh}
            </button>
          </div>

          {!operatorIdValid ? <div className="warning-inline">{t.setOperatorId}</div> : null}
        </header>

        {contractMismatch ? <div className="error-banner">{t.contractMismatch}</div> : null}

        {handshakeError ? (
          <div className="error-banner">
            <div>{`${handshakeError.code}: ${handshakeError.message}`}</div>
            <small>{handshakeError.command}</small>
          </div>
        ) : null}

        {activeView === 'dashboard' ? (
          <section className="panel-grid">
            <article className="panel-card">
              <h3>{t.pendingApprovals}</h3>
              <p className="metric">{pendingApprovals.length}</p>
            </article>
            <article className="panel-card">
              <h3>{t.recentRuns}</h3>
              <p className="metric">{runItems.length}</p>
            </article>
            <article className="panel-card wide">
              <h3>{t.capabilities}</h3>
              <pre>{JSON.stringify(capabilities, null, 2)}</pre>
            </article>
            <article className="panel-card wide">
              <h3>{t.doctor}</h3>
              <pre>{JSON.stringify(handshakeRecord.doctor ?? {}, null, 2)}</pre>
            </article>
          </section>
        ) : null}

        {activeView === 'approvals' ? (
          <section className="split-view">
            <div className="list-pane">
              <div className="pane-head">
                <h3>{t.pendingApprovals}</h3>
                <button className="ghost-btn" type="button" onClick={() => void refreshApprovals()}>
                  {t.refresh}
                </button>
              </div>
              <div className="list-scroll">
                {pendingApprovals.length === 0 ? <p>{t.noData}</p> : null}
                {pendingApprovals.map((item) => {
                  const row = asRecord(item);
                  const approvalId = readString(row, 'approval_id');
                  return (
                    <button
                      key={approvalId}
                      type="button"
                      className={approvalId === selectedApprovalId ? 'row row-active' : 'row'}
                      onClick={() => setSelectedApprovalId(approvalId)}
                    >
                      <strong>{approvalId}</strong>
                      <span>{readString(row, 'status')}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="detail-pane">
              <div className="pane-head">
                <h3>{t.selectedApproval}</h3>
              </div>

              <div className="action-row">
                <button className="action-btn" type="button" disabled={!canMutate || !selectedApprovalId} onClick={() => void onApprove(true)}>
                  {t.approve}
                </button>
                <button className="action-btn" type="button" disabled={!canMutate || !selectedApprovalId} onClick={() => void onApprove(false)}>
                  {t.reject}
                </button>
                <button className="action-btn action-danger" type="button" disabled={!canMutate || !selectedApprovalId} onClick={() => void onExecute()}>
                  {t.execute}
                </button>
              </div>

              <pre>{JSON.stringify(selectedApproval, null, 2)}</pre>
            </div>
          </section>
        ) : null}

        {activeView === 'runs' ? (
          <section className="split-view">
            <div className="list-pane">
              <div className="pane-head">
                <h3>{t.recentRuns}</h3>
                <button className="ghost-btn" type="button" onClick={() => void refreshRuns()}>
                  {t.refresh}
                </button>
              </div>

              <div className="list-scroll">
                {runItems.length === 0 ? <p>{t.noData}</p> : null}
                {runItems.map((item) => {
                  const row = asRecord(item);
                  const jobId = readString(row, 'job_id');
                  return (
                    <button
                      key={jobId}
                      type="button"
                      className={jobId === selectedRunId ? 'row row-active' : 'row'}
                      onClick={() => setSelectedRunId(jobId)}
                    >
                      <strong>{jobId}</strong>
                      <span>{readString(row, 'status')}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="detail-pane">
              <div className="pane-head">
                <h3>{t.runDetail}</h3>
                <button className="ghost-btn" type="button" disabled={!selectedRunId} onClick={() => void onExportArtifacts()}>
                  {t.export}
                </button>
              </div>

              {!selectedRunId ? <p>{t.selectRun}</p> : null}

              {selectedRunId ? (
                <>
                  <div className="tab-row">
                    {(['overview', 'timeline', 'artifacts', 'replay'] as RunTabKey[]).map((tab) => (
                      <button
                        key={tab}
                        type="button"
                        className={tab === runTab ? 'tab-btn tab-btn-active' : 'tab-btn'}
                        onClick={() => setRunTab(tab)}
                      >
                        {tab === 'overview'
                          ? t.overview
                          : tab === 'timeline'
                            ? t.timeline
                            : tab === 'artifacts'
                              ? t.artifacts
                              : t.replay}
                      </button>
                    ))}
                  </div>

                  {runTab === 'overview' ? <pre>{JSON.stringify(runStatus, null, 2)}</pre> : null}

                  {runTab === 'timeline' ? (
                    <div className="timeline-pane">
                      {eventsWarning ? <div className="warning-inline">{eventsWarning}</div> : null}
                      {events.length === 0 ? <p>{t.noData}</p> : null}
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

                  {runTab === 'artifacts' ? (
                    <div>
                      <div className="artifact-controls">
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
                          onClick={() => {
                            if (!settings.debugRaw) {
                              return;
                            }
                            if (!showRawArtifact) {
                              const confirmed = window.confirm('Show raw payload?');
                              if (!confirmed) {
                                return;
                              }
                            }
                            setShowRawArtifact((prev) => !prev);
                          }}
                        >
                          {showRawArtifact ? t.hideRaw : t.showRaw}
                        </button>
                      </div>

                      {!showRawArtifact ? (
                        <pre>{JSON.stringify(artifactValue ?? {}, null, 2)}</pre>
                      ) : (
                        <pre>{JSON.stringify(parsedArtifact, null, 2)}</pre>
                      )}
                    </div>
                  ) : null}

                  {runTab === 'replay' ? <pre>{JSON.stringify(runReplay, null, 2)}</pre> : null}
                </>
              ) : null}
            </div>
          </section>
        ) : null}

        {activeView === 'diagnostics' ? (
          <section className="panel-grid">
            <article className="panel-card">
              <h3>{t.uiVersion}</h3>
              <p className="mono">{readString(handshakeRecord, 'uiVersion', '-')}</p>
            </article>
            <article className="panel-card">
              <h3>{t.coreVersion}</h3>
              <p className="mono">{readString(handshakeRecord, 'coreVersion', '-')}</p>
            </article>
            <article className="panel-card">
              <h3>{t.contractVersion}</h3>
              <p className="mono">{readString(handshakeRecord, 'contractVersion', '-')}</p>
            </article>
            <article className="panel-card wide">
              <h3>{t.capabilities}</h3>
              <pre>{JSON.stringify(capabilities, null, 2)}</pre>
            </article>
            <article className="panel-card wide">
              <h3>{t.doctor}</h3>
              <pre>{JSON.stringify(handshakeRecord.doctor ?? {}, null, 2)}</pre>
            </article>
          </section>
        ) : null}

        {activeView === 'settings' ? (
          <section className="settings-form">
            <div className="form-row">
              <label htmlFor="operator-id">{t.operatorId}</label>
              <input
                id="operator-id"
                value={settings.operatorId}
                onChange={(event) => updateSettings({ operatorId: event.target.value })}
                placeholder="ops-team-01"
              />
            </div>

            <div className="form-row">
              <label htmlFor="profile">{t.profile}</label>
              <input
                id="profile"
                value={settings.profile}
                onChange={(event) => updateSettings({ profile: event.target.value })}
              />
            </div>

            <div className="form-row">
              <label htmlFor="root-dir">{t.rootDir}</label>
              <input
                id="root-dir"
                value={settings.rootDir}
                onChange={(event) => updateSettings({ rootDir: event.target.value })}
              />
            </div>

            <div className="form-row">
              <label htmlFor="mode">{t.mode}</label>
              <select id="mode" value={settings.mode} onChange={(event) => updateSettings({ mode: event.target.value as PanelSettings['mode'] })}>
                <option value="auto">auto</option>
                <option value="external">external</option>
                <option value="bundled">bundled</option>
              </select>
            </div>

            <div className="form-row">
              <label htmlFor="cli-path">{t.cliPath}</label>
              <input
                id="cli-path"
                value={settings.cliPath}
                onChange={(event) => updateSettings({ cliPath: event.target.value })}
                placeholder="/usr/local/bin/binliquid"
              />
            </div>

            <div className="form-row">
              <label htmlFor="bundled-python-path">{t.bundledPythonPath}</label>
              <input
                id="bundled-python-path"
                value={settings.bundledPythonPath}
                onChange={(event) => updateSettings({ bundledPythonPath: event.target.value })}
                placeholder=".../Contents/Resources/binliquid-runtime/python/bin/python"
              />
            </div>

            <div className="form-row">
              <label htmlFor="locale">{t.locale}</label>
              <select
                id="locale"
                value={settings.locale}
                onChange={(event) => updateSettings({ locale: event.target.value as LocaleMode })}
              >
                <option value="auto">auto</option>
                <option value="en">English</option>
                <option value="tr">Türkçe</option>
              </select>
            </div>

            <div className="form-row">
              <label htmlFor="updater-mode">{t.updaterMode}</label>
              <select
                id="updater-mode"
                value={settings.updaterMode}
                onChange={(event) =>
                  updateSettings({ updaterMode: event.target.value as PanelSettings['updaterMode'] })
                }
              >
                <option value="off">off</option>
                <option value="manual">manual</option>
                <option value="auto">auto</option>
              </select>
            </div>

            <div className="form-row form-row-inline">
              <label htmlFor="remote-telemetry">{t.remoteTelemetry}</label>
              <input
                id="remote-telemetry"
                type="checkbox"
                checked={settings.remoteTelemetry}
                onChange={(event) => updateSettings({ remoteTelemetry: event.target.checked })}
              />
            </div>

            <div className="form-row form-row-inline">
              <label htmlFor="debug-raw">{t.debugRaw}</label>
              <input
                id="debug-raw"
                type="checkbox"
                checked={settings.debugRaw}
                onChange={(event) => updateSettings({ debugRaw: event.target.checked })}
              />
            </div>

            <button
              type="button"
              className="action-btn"
              onClick={() => {
                saveSettings(settings);
                pushToast('ok', t.saved);
              }}
            >
              {t.save}
            </button>
          </section>
        ) : null}
      </main>

      <div className="toast-zone">
        {toasts.map((toast) => (
          <div className={toast.kind === 'error' ? 'toast toast-error' : 'toast'} key={toast.id}>
            {toast.text}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
