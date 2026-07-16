import { describe, expect, it } from 'vitest';

import {
  parseDocumentArtifactContent,
  selectionFromBlockIds,
  serializeDocumentBlocks,
} from './documentAdapter';

describe('document artifact adapter', () => {
  it('preserves stable native BlockNote IDs through parse and serialize', () => {
    const content = parseDocumentArtifactContent({
      kind: 'document',
      schemaVersion: 1,
      language: 'en',
      pageMode: 'document',
      blocks: [
        {
          id: 'block-stable-1',
          type: 'paragraph',
          props: { textAlignment: 'left', textColor: 'default', backgroundColor: 'default' },
          content: [{ type: 'text', text: 'Governed draft', styles: {} }],
          children: [],
        },
      ],
    });

    const serialized = serializeDocumentBlocks(content, content.blocks);

    expect(serialized.blocks[0]).toMatchObject({ id: 'block-stable-1', type: 'paragraph' });
    expect(serialized.language).toBe('en');
    expect(serialized.pageMode).toBe('document');
  });

  it.each([
    ['remote link', [{ id: 'block-1', type: 'paragraph', content: [{ type: 'link', href: 'https://example.com', content: [] }] }]],
    ['remote embed', [{ id: 'block-1', type: 'image', props: { url: 'https://example.com/a.png' }, content: [] }]],
    ['missing stable id', [{ type: 'paragraph', content: [] }]],
  ])('rejects unsafe or unstable %s before editor mount', (_label, blocks) => {
    expect(() =>
      parseDocumentArtifactContent({
        kind: 'document',
        schemaVersion: 1,
        language: 'en',
        pageMode: 'document',
        blocks,
      }),
    ).toThrow();
  });

  it('projects bounded block selections without raw text', () => {
    expect(selectionFromBlockIds(['block-1', 'block-2', 'block-2'])).toEqual({
      kind: 'block',
      blockIds: ['block-1', 'block-2'],
      anchorBlockId: 'block-1',
      focusBlockId: 'block-2',
    });
    expect(selectionFromBlockIds([])).toBeNull();
  });
});
