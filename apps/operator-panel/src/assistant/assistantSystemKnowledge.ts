export type AssistantKnowledgeIntent =
  | 'platform_usage'
  | 'agent_task'
  | 'approval'
  | 'run_evidence'
  | 'provider'
  | 'memory'
  | 'computer_use'
  | 'deployment'
  | 'unknown';

export type AssistantKnowledgeStatus = 'ready' | 'no_hits' | 'stale' | 'blocked';

export interface AssistantKnowledgeHit {
  chunkId: string;
  path: string;
  heading: string;
  snippet: string;
  score: number;
  matchedTerms: string[];
  commands: string[];
  sourceHash: string;
}

export interface AssistantSystemKnowledgeContext {
  status: 'available' | 'unavailable' | 'stale' | 'blocked';
  identityBrief: string;
  answerRules: string[];
  sources: AssistantKnowledgeHit[];
  contextText: string;
  omittedSources: string[];
  blockingReasons: string[];
}

export interface AssistantKnowledgeSearchResponse {
  contractVersion: 'operator-panel.assistant-system-knowledge/v1';
  status: AssistantKnowledgeStatus;
  intent: AssistantKnowledgeIntent;
  hits: AssistantKnowledgeHit[];
  contextText: string;
  context: AssistantSystemKnowledgeContext;
  blockingReasons: string[];
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function readString(source: Record<string, unknown>, key: string, fallback = ''): string {
  const value = source[key];
  return typeof value === 'string' ? value : fallback;
}

function readStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

export function normalizeAssistantKnowledgeHit(value: unknown): AssistantKnowledgeHit {
  const record = asRecord(value);
  return {
    chunkId: readString(record, 'chunkId'),
    path: readString(record, 'path'),
    heading: readString(record, 'heading'),
    snippet: readString(record, 'snippet'),
    score: typeof record.score === 'number' ? record.score : 0,
    matchedTerms: readStringArray(record.matchedTerms),
    commands: readStringArray(record.commands),
    sourceHash: readString(record, 'sourceHash'),
  };
}

export function normalizeAssistantSystemKnowledgeContext(value: unknown): AssistantSystemKnowledgeContext {
  const record = asRecord(value);
  const rawStatus = readString(record, 'status', 'unavailable');
  const status: AssistantSystemKnowledgeContext['status'] =
    rawStatus === 'available' || rawStatus === 'stale' || rawStatus === 'blocked' ? rawStatus : 'unavailable';
  return {
    status,
    identityBrief: readString(record, 'identityBrief'),
    answerRules: readStringArray(record.answerRules),
    sources: Array.isArray(record.sources) ? record.sources.map(normalizeAssistantKnowledgeHit) : [],
    contextText: readString(record, 'contextText'),
    omittedSources: readStringArray(record.omittedSources),
    blockingReasons: readStringArray(record.blockingReasons),
  };
}

export function normalizeAssistantKnowledgeSearchResponse(value: unknown): AssistantKnowledgeSearchResponse {
  const record = asRecord(value);
  const rawStatus = readString(record, 'status', 'blocked');
  const status: AssistantKnowledgeStatus =
    rawStatus === 'ready' || rawStatus === 'no_hits' || rawStatus === 'stale' ? rawStatus : 'blocked';
  const context = normalizeAssistantSystemKnowledgeContext(record.context);
  return {
    contractVersion: 'operator-panel.assistant-system-knowledge/v1',
    status,
    intent: readString(record, 'intent', 'unknown') as AssistantKnowledgeIntent,
    hits: Array.isArray(record.hits) ? record.hits.map(normalizeAssistantKnowledgeHit) : [],
    contextText: readString(record, 'contextText', context.contextText),
    context,
    blockingReasons: readStringArray(record.blockingReasons),
  };
}

export function previewAssistantKnowledgeSearch(query: string): AssistantKnowledgeSearchResponse {
  const hit: AssistantKnowledgeHit = {
    chunkId: 'docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md#preview',
    path: 'docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md',
    heading: query.toLowerCase().includes('agent') ? 'Giving An Agent A Task' : 'AegisOS Identity',
    snippet:
      'AegisOS/BinLiquid is grounded from local system knowledge docs, CLI contracts, route manifests, and runtime snapshots.',
    score: 0.92,
    matchedTerms: ['aegisos', 'agent'],
    commands: ['uv run binliquid assistant knowledge search --profile enterprise --query "..." --json'],
    sourceHash: 'preview',
  };
  const context: AssistantSystemKnowledgeContext = {
    status: 'available',
    identityBrief:
      'AegisOS/BinLiquid is a self-hosted single-organization enterprise Agent Control Plane.',
    answerRules: [
      'Use local system knowledge sources for AegisOS platform claims.',
      'Do not guess when verified local sources are unavailable.',
    ],
    sources: [hit],
    contextText: `Source: ${hit.path}\nHeading: ${hit.heading}\nSnippet: ${hit.snippet}`,
    omittedSources: [],
    blockingReasons: [],
  };
  return {
    contractVersion: 'operator-panel.assistant-system-knowledge/v1',
    status: 'ready',
    intent: query.toLowerCase().includes('agent') ? 'agent_task' : 'platform_usage',
    hits: [hit],
    contextText: context.contextText,
    context,
    blockingReasons: [],
  };
}
