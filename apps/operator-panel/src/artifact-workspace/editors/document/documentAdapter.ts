import type { ArtifactContent } from '../../artifactContracts';

const ALLOWED_BLOCK_TYPES = new Set([
  'paragraph',
  'heading',
  'bulletListItem',
  'numberedListItem',
  'checkListItem',
  'quote',
  'codeBlock',
  'divider',
]);
const BOUNDED_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/;
const LANGUAGE = /^[a-z]{2,3}(?:-[A-Z]{2})?$/;
const MAX_BLOCKS = 10_000;
const MAX_DEPTH = 20;
const MAX_BYTES = 5 * 1024 * 1024;

export type DocumentTextNode = {
  type: 'text';
  text: string;
  styles: Record<string, boolean | string>;
};

export type DocumentBlock = {
  id: string;
  type: string;
  props: Record<string, boolean | number | string>;
  content: DocumentTextNode[];
  children: DocumentBlock[];
};

export type DocumentArtifactContent = ArtifactContent & {
  kind: 'document';
  schemaVersion: 1;
  language: string;
  pageMode: 'document' | 'paginated';
  blocks: DocumentBlock[];
};

export type DocumentArtifactSelection = {
  kind: 'block';
  blockIds: string[];
  anchorBlockId: string;
  focusBlockId: string;
};

function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${label} must be an object.`);
  }
  return value as Record<string, unknown>;
}

function assertKeys(value: Record<string, unknown>, allowed: string[], label: string): void {
  const unknown = Object.keys(value).filter((key) => !allowed.includes(key));
  if (unknown.length > 0) throw new Error(`${label} contains unsupported fields.`);
}

function containsRemoteUrl(value: unknown): boolean {
  if (typeof value === 'string') return /^(?:https?:)?\/\//i.test(value.trim());
  if (Array.isArray(value)) return value.some(containsRemoteUrl);
  if (typeof value === 'object' && value !== null) return Object.values(value).some(containsRemoteUrl);
  return false;
}

function parseStyles(value: unknown): Record<string, boolean | string> {
  if (value === undefined) return {};
  const source = record(value, 'Text styles');
  const result: Record<string, boolean | string> = {};
  for (const [key, item] of Object.entries(source)) {
    if (typeof item !== 'boolean' && typeof item !== 'string') throw new Error('Text style value is invalid.');
    result[key] = item;
  }
  return result;
}

function parseTextNode(value: unknown): DocumentTextNode {
  const source = record(value, 'Inline content');
  assertKeys(source, ['type', 'text', 'styles'], 'Inline content');
  if (source.type !== 'text' || typeof source.text !== 'string') {
    throw new Error('Only native text inline content is allowed.');
  }
  return { type: 'text', text: source.text, styles: parseStyles(source.styles) };
}

function parseProps(value: unknown): Record<string, boolean | number | string> {
  if (value === undefined) return {};
  const source = record(value, 'Block props');
  const result: Record<string, boolean | number | string> = {};
  for (const [key, item] of Object.entries(source)) {
    if (item === undefined) continue;
    if (!['boolean', 'number', 'string'].includes(typeof item)) throw new Error('Block prop is invalid.');
    result[key] = item as boolean | number | string;
  }
  return result;
}

function parseBlock(value: unknown, depth: number, count: { value: number }): DocumentBlock {
  if (depth > MAX_DEPTH) throw new Error('Document block depth exceeded.');
  count.value += 1;
  if (count.value > MAX_BLOCKS) throw new Error('Document block count exceeded.');
  const source = record(value, 'Document block');
  assertKeys(source, ['id', 'type', 'props', 'content', 'children'], 'Document block');
  if (typeof source.id !== 'string' || !BOUNDED_ID.test(source.id)) {
    throw new Error('Document block requires a stable bounded ID.');
  }
  if (typeof source.type !== 'string' || !ALLOWED_BLOCK_TYPES.has(source.type)) {
    throw new Error('Document block type is not allowed.');
  }
  const rawContent = source.content ?? [];
  if (!Array.isArray(rawContent)) throw new Error('Document block content must be an array.');
  const rawChildren = source.children ?? [];
  if (!Array.isArray(rawChildren)) throw new Error('Document block children must be an array.');
  return {
    id: source.id,
    type: source.type,
    props: parseProps(source.props),
    content: rawContent.map(parseTextNode),
    children: rawChildren.map((child) => parseBlock(child, depth + 1, count)),
  };
}

export function parseDocumentArtifactContent(value: unknown): DocumentArtifactContent {
  if (containsRemoteUrl(value)) throw new Error('Remote document content is forbidden.');
  const serialized = JSON.stringify(value);
  if (new TextEncoder().encode(serialized).byteLength > MAX_BYTES) throw new Error('Document content is too large.');
  const source = record(value, 'Document content');
  assertKeys(source, ['kind', 'schemaVersion', 'language', 'pageMode', 'blocks'], 'Document content');
  if (source.kind !== 'document' || source.schemaVersion !== 1) throw new Error('Document contract version is invalid.');
  if (typeof source.language !== 'string' || !LANGUAGE.test(source.language)) throw new Error('Document language is invalid.');
  if (source.pageMode !== 'document' && source.pageMode !== 'paginated') throw new Error('Document page mode is invalid.');
  if (!Array.isArray(source.blocks)) throw new Error('Document blocks must be an array.');
  const count = { value: 0 };
  return {
    kind: 'document',
    schemaVersion: 1,
    language: source.language,
    pageMode: source.pageMode,
    blocks: source.blocks.map((block) => parseBlock(block, 1, count)),
  };
}

export function serializeDocumentBlocks(
  base: DocumentArtifactContent,
  blocks: unknown,
): DocumentArtifactContent {
  return parseDocumentArtifactContent({ ...base, blocks });
}

export function selectionFromBlockIds(blockIds: string[]): DocumentArtifactSelection | null {
  const unique = Array.from(new Set(blockIds.filter((id) => BOUNDED_ID.test(id)))).slice(0, 500);
  if (unique.length === 0) return null;
  return {
    kind: 'block',
    blockIds: unique,
    anchorBlockId: unique[0],
    focusBlockId: unique.at(-1) ?? unique[0],
  };
}
