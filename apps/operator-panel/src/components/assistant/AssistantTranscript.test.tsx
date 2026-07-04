import { fireEvent, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { AssistantTurn } from '../../assistant/assistantTypes';
import { renderOperatorPanel } from '../../test/render';
import { AssistantTranscript } from './AssistantTranscript';

const baseTurn: AssistantTurn = {
  id: 'turn-1',
  startedAtUtc: '2026-03-08T09:20:00Z',
  completedAtUtc: null,
  composerControls: null,
  status: 'streaming',
  eventSequence: 1,
  userMessage: {
    id: 'turn-1-user',
    text: 'Summarize this run.',
    createdAtUtc: '2026-03-08T09:20:00Z',
  },
  assistantMessage: {
    id: 'turn-1-assistant',
    text: 'Working...',
    findings: [],
    timeline: [],
    proposedAction: null,
    approval: null,
    referencedRuns: [],
    referencedArtifacts: [],
    metrics: null,
    warning: null,
    error: null,
  },
};

const noop = () => undefined;

function renderTranscript(turns: AssistantTurn[]) {
  return renderOperatorPanel(
    <AssistantTranscript
      turns={turns}
      approvalDisabled={false}
      approvalDisabledReason=""
      emptyRunLabel="No run"
      debugRawEnabled={false}
      onReviewApproval={noop}
      onApprove={noop}
      onReject={noop}
      onExecute={noop}
      onRegenerate={noop}
    />,
  );
}

describe('AssistantTranscript sticky scrolling', () => {
  let scrollHeightValue = 1000;
  let clientHeightValue = 500;
  let scrollTops: WeakMap<HTMLElement, number>;
  let scrollToMock: ReturnType<typeof vi.fn>;
  let originalScrollHeight: PropertyDescriptor | undefined;
  let originalClientHeight: PropertyDescriptor | undefined;
  let originalScrollTop: PropertyDescriptor | undefined;
  let originalScrollTo: typeof HTMLElement.prototype.scrollTo;

  beforeEach(() => {
    scrollHeightValue = 1000;
    clientHeightValue = 500;
    scrollTops = new WeakMap();
    scrollToMock = vi.fn(function scrollTo(this: HTMLElement, options?: ScrollToOptions | number) {
      const top = typeof options === 'number' ? options : Number(options?.top ?? 0);
      scrollTops.set(this, top);
    });
    originalScrollHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollHeight');
    originalClientHeight = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientHeight');
    originalScrollTop = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollTop');
    originalScrollTo = HTMLElement.prototype.scrollTo;

    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
      configurable: true,
      get() {
        return this.classList?.contains('assistant-transcript') ? scrollHeightValue : 0;
      },
    });
    Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
      configurable: true,
      get() {
        return this.classList?.contains('assistant-transcript') ? clientHeightValue : 0;
      },
    });
    Object.defineProperty(HTMLElement.prototype, 'scrollTop', {
      configurable: true,
      get() {
        return scrollTops.get(this) ?? 0;
      },
      set(value: number) {
        scrollTops.set(this, value);
      },
    });
    HTMLElement.prototype.scrollTo = scrollToMock as unknown as typeof HTMLElement.prototype.scrollTo;
  });

  afterEach(() => {
    if (originalScrollHeight) {
      Object.defineProperty(HTMLElement.prototype, 'scrollHeight', originalScrollHeight);
    }
    if (originalClientHeight) {
      Object.defineProperty(HTMLElement.prototype, 'clientHeight', originalClientHeight);
    }
    if (originalScrollTop) {
      Object.defineProperty(HTMLElement.prototype, 'scrollTop', originalScrollTop);
    }
    HTMLElement.prototype.scrollTo = originalScrollTo;
  });

  it('anchors the newest turn start when a new turn appears', () => {
    renderTranscript([baseTurn]);

    expect(scrollToMock).toHaveBeenCalledWith(expect.objectContaining({ top: 0 }));
    expect(scrollToMock).not.toHaveBeenCalledWith(expect.objectContaining({ top: 1000 }));
  });

  it('keeps the current position when the user has scrolled away from latest content', () => {
    const { rerender } = renderTranscript([baseTurn]);
    const transcript = screen.getByRole('log');
    scrollToMock.mockClear();

    transcript.scrollTop = 100;
    fireEvent.wheel(transcript);
    fireEvent.scroll(transcript);
    scrollHeightValue = 1500;

    rerender(
      <AssistantTranscript
        turns={[
          {
            ...baseTurn,
            assistantMessage: {
              ...baseTurn.assistantMessage,
              text: `${baseTurn.assistantMessage.text} More streamed content.`,
            },
          },
        ]}
        approvalDisabled={false}
        approvalDisabledReason=""
        emptyRunLabel="No run"
        debugRawEnabled={false}
        onReviewApproval={noop}
        onApprove={noop}
        onReject={noop}
        onExecute={noop}
        onRegenerate={noop}
      />,
    );

    expect(scrollToMock).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Jump to latest' })).toBeInTheDocument();
  });

  it('lets the user jump back to the latest turn', async () => {
    const { user } = renderTranscript([baseTurn]);
    const transcript = screen.getByRole('log');
    scrollToMock.mockClear();

    transcript.scrollTop = 100;
    fireEvent.wheel(transcript);
    fireEvent.scroll(transcript);
    await user.click(screen.getByRole('button', { name: 'Jump to latest' }));

    expect(scrollToMock).toHaveBeenCalledWith(expect.objectContaining({ top: 1000 }));
  });
});
