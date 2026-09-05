import { useEffect } from 'react';
import { screen } from '@testing-library/react';
import { it, expect, vi } from 'vitest';
import { renderOperatorPanel } from '../../test/render';
const lifecycle = vi.hoisted(() => ({start:vi.fn(),stop:vi.fn()}));
vi.mock('../terminal/TerminalSurface', () => ({TerminalSurface: () => { useEffect(() => {lifecycle.start(); return () => lifecycle.stop();}, []); return <div>Live terminal</div>; }}));
import { TerminalDock } from './TerminalDock';
it('preserves terminals when switching tabs and hiding the dock, closes only the requested session', async () => {
  const {user,rerender} = renderOperatorPanel(<TerminalDock open projectRootRef="root"/>);
  expect(lifecycle.start).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole('button',{name:'Yeni terminal'}));
  expect(lifecycle.start).toHaveBeenCalledTimes(2);
  await user.click(screen.getByRole('tab',{name:'Terminal 1'}));
  rerender(<TerminalDock open={false} projectRootRef="root"/>);
  expect(lifecycle.stop).not.toHaveBeenCalled();
  rerender(<TerminalDock open projectRootRef="root"/>);
  await user.click(screen.getByRole('button',{name:'Terminal 2 kapat'}));
  expect(lifecycle.stop).toHaveBeenCalledTimes(1);
});
