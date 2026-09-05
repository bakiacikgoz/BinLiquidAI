import { act, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { renderOperatorPanel } from '../../test/render';
import { getAssistantFixture } from '../../assistant/assistantFixtures';
import { TurnActivity } from './TurnActivity';

describe('TurnActivity', () => {
  it('advances elapsed time only while working and exposes real event details', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-09-05T10:00:10Z'));
    const turn = getAssistantFixture('running').turns[0];
    turn.startedAtUtc = '2026-09-05T10:00:00Z';
    turn.completedAtUtc = null;
    turn.assistantMessage.timeline = [{ id: 'event', tone: 'success', title: 'Dosya düzenlendi', subtitle: 'src/app.tsx', timestampUtc: turn.startedAtUtc }];
    const { rerender, unmount } = renderOperatorPanel(<TurnActivity turn={turn} />);
    expect(screen.getByText('10 sn süredir çalışıyor')).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Çalışma adımları' })).toBeVisible();
    act(() => vi.advanceTimersByTime(2000));
    expect(screen.getByText('12 sn süredir çalışıyor')).toBeInTheDocument();
    rerender(<TurnActivity turn={{ ...turn, status: 'completed', completedAtUtc: '2026-09-05T10:00:12Z' }} />);
    act(() => vi.advanceTimersByTime(3000));
    expect(screen.getByText('12 sn çalıştı')).toBeInTheDocument();
    unmount();
    vi.useRealTimers();
  });
});
