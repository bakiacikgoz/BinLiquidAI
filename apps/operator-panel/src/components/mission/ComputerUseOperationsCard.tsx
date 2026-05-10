import {
  type ComputerUseCapability,
  type ComputerUseRuntimeChoice,
  type ComputerUseVisionRuntimeCapability,
} from '../../capabilities';

type SummaryCounts = {
  success: number;
  blocked: number;
  failed: number;
  stopped: number;
  active: number;
};

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readNumber(source: Record<string, unknown>, key: string): number {
  const value = source[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function readStringArray(source: Record<string, unknown>, key: string): string[] {
  const value = source[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function readCounts(summary: unknown): SummaryCounts {
  const counts = asRecord(asRecord(summary).counts);
  return {
    success: readNumber(counts, 'success'),
    blocked: readNumber(counts, 'blocked'),
    failed: readNumber(counts, 'failed'),
    stopped: readNumber(counts, 'stopped'),
    active: readNumber(counts, 'active'),
  };
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.map((item) => item.trim()).filter(Boolean)));
}

function safetyWarnings(capability: ComputerUseVisionRuntimeCapability): string[] {
  const resolution = capability.capabilityResolution;
  const warnings: string[] = [];
  if (capability.safety.rawScreenshotPersistence !== 'disabled') {
    warnings.push('raw screenshot persistence drift');
  }
  if (capability.safety.terminalControl !== 'deny') {
    warnings.push('terminal control must remain deny');
  }
  if (resolution?.safety.failClosed === false) {
    warnings.push('fail-closed safety is required');
  }
  if (resolution?.config.rawScreenshotPersistence === true) {
    warnings.push('raw screenshots must remain disabled');
  }
  if (resolution && resolution.config.terminalPolicy !== 'deny') {
    warnings.push('terminal policy must remain deny');
  }
  if (resolution?.safety.sensitiveSurfaceStopEnabled === false) {
    warnings.push('sensitive surface stop must remain enabled');
  }
  return warnings;
}

export function ComputerUseOperationsCard({
  legacyCapability,
  visionCapability,
  summary,
  runtimeChoice,
  startAllowed,
  disabledReason,
  blockers,
  onRuntimeChoiceChange,
}: {
  legacyCapability: ComputerUseCapability;
  visionCapability: ComputerUseVisionRuntimeCapability;
  summary: unknown;
  runtimeChoice: ComputerUseRuntimeChoice;
  startAllowed: boolean;
  disabledReason: string;
  blockers: string[];
  onRuntimeChoiceChange: (choice: ComputerUseRuntimeChoice) => void;
}) {
  const counts = readCounts(summary);
  const summaryRecord = asRecord(summary);
  const topFailureCodes = readStringArray(summaryRecord, 'top_failure_codes');
  const failureRows = Array.isArray(summaryRecord.top_failure_codes)
    ? summaryRecord.top_failure_codes.map((item) => asRecord(item)).slice(0, 3)
    : [];
  const readinessBlockers = readStringArray(summaryRecord, 'readiness_blockers');
  const mergedBlockers = unique([...blockers, ...readinessBlockers]).slice(0, 6);
  const warnings = safetyWarnings(visionCapability);
  const selectedLegacy = runtimeChoice === 'legacy-pilot';
  const safeNextAction = startAllowed
    ? 'Start supervised run only after local operator confirmation.'
    : 'Run doctor/preflight; do not start live automation.';
  const reasonCode =
    selectedLegacy
      ? legacyCapability.reasonCode
      : visionCapability.reasonCode || visionCapability.capabilityResolution?.reasonCode;

  return (
    <article className="page-card computer-use-operations-card">
      <div className="computer-use-operations-head">
        <h3>Computer-Use Operations</h3>
        <span className={startAllowed ? 'pill pill-success' : 'pill pill-warning'}>
          {startAllowed ? 'Live gate ready' : 'Live gate blocked'}
        </span>
      </div>

      <label className="field">
        <span>Runtime</span>
        <select
          aria-label="Computer-use runtime"
          value={runtimeChoice}
          onChange={(event) => onRuntimeChoiceChange(event.target.value as ComputerUseRuntimeChoice)}
        >
          <option value="vision-first">vision-first</option>
          <option value="legacy-pilot">legacy-pilot</option>
          <option value="auto">auto</option>
        </select>
      </label>

      {selectedLegacy ? (
        <div className="warning-inline">
          Legacy pilot selected. Vision-first qualification gate is bypassed only for the legacy pilot path; keep
          this local and supervised.
        </div>
      ) : null}

      <div className="metric-list">
        <div className="metric-row">
          <span>Platform</span>
          <strong>{selectedLegacy ? legacyCapability.platform : visionCapability.platform}</strong>
        </div>
        <div className="metric-row">
          <span>Stage</span>
          <strong>{selectedLegacy ? legacyCapability.stage : visionCapability.stage}</strong>
        </div>
        <div className="metric-row">
          <span>Reason code</span>
          <strong>{reasonCode || '-'}</strong>
        </div>
        <div className="metric-row">
          <span>Raw screenshots</span>
          <strong>{visionCapability.safety.rawScreenshotPersistence}</strong>
        </div>
        <div className="metric-row">
          <span>Terminal policy</span>
          <strong>{visionCapability.safety.terminalControl}</strong>
        </div>
        <div className="metric-row">
          <span>Sensitive surface</span>
          <strong>{visionCapability.capabilityResolution?.safety.sensitiveSurfaceStopEnabled === false ? 'drift' : 'stop'}</strong>
        </div>
      </div>

      <div className="computer-use-count-grid" aria-label="Computer-use recent outcome counts">
        {Object.entries(counts).map(([key, value]) => (
          <div className="computer-use-count" key={key}>
            <span>{key}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      {failureRows.length > 0 ? (
        <div className="computer-use-chip-row" aria-label="Computer-use top failure codes">
          {failureRows.map((item) => (
            <span className="pill" key={`${readString(item, 'code')}-${readNumber(item, 'count')}`}>
              {readString(item, 'code') || 'unknown'} ({readNumber(item, 'count')})
            </span>
          ))}
        </div>
      ) : topFailureCodes.length > 0 ? (
        <div className="computer-use-chip-row" aria-label="Computer-use top failure codes">
          {topFailureCodes.map((code) => (
            <span className="pill" key={code}>
              {code}
            </span>
          ))}
        </div>
      ) : null}

      {mergedBlockers.length > 0 ? (
        <div className="computer-use-chip-row" aria-label="Computer-use blockers">
          {mergedBlockers.map((blocker) => (
            <span className="pill" key={blocker}>
              {blocker}
            </span>
          ))}
        </div>
      ) : null}

      {warnings.length > 0 ? <div className="warning-inline">{warnings.join(', ')}</div> : null}
      {!startAllowed && disabledReason ? <div className="warning-inline">{disabledReason}</div> : null}
      <p className="supporting">{safeNextAction}</p>
    </article>
  );
}
