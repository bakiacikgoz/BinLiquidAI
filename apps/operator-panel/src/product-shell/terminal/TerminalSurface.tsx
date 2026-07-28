import '@xterm/xterm/css/xterm.css';

import { FitAddon } from '@xterm/addon-fit';
import { SearchAddon } from '@xterm/addon-search';
import { Terminal } from '@xterm/xterm';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useEffect, useRef, useState } from 'react';

type StartResponse = { sessionId: string; shell: string };
type OutputEvent = { sessionId: string; data: string };

function decodeBase64(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (character) => character.charCodeAt(0));
}

export function TerminalSurface({ active = true, onClose, projectRootRef, projectRootDisplayName }: { active?: boolean; onClose: () => void; projectRootRef?: string; projectRootDisplayName?: string }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<string | null>(null);
  const activeRef = useRef(active);
  const [error, setError] = useState('');

  useEffect(() => { activeRef.current = active; }, [active]);

  useEffect(() => {
    if (!hostRef.current) return;
    const terminal = new Terminal({ cursorBlink: true, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', theme: { background: '#0b1016', foreground: '#e8eef7' } });
    const fit = new FitAddon(); const search = new SearchAddon();
    terminal.loadAddon(fit); terminal.loadAddon(search); terminal.open(hostRef.current); fit.fit();
    const resize = new ResizeObserver(() => { if (!activeRef.current) return; fit.fit(); if (sessionRef.current && terminal.cols > 0 && terminal.rows > 0) void invoke('terminal_resize', { request: { sessionId: sessionRef.current, cols: terminal.cols, rows: terminal.rows } }); });
    resize.observe(hostRef.current);
    let unlisten: (() => void) | undefined;
    const start = async () => {
      try {
        const session = await invoke<StartResponse>('terminal_start', { request: { mode: 'user', rootRef: projectRootRef, cols: terminal.cols || 80, rows: terminal.rows || 24 } });
        sessionRef.current = session.sessionId; terminal.writeln(`\x1b[32mImperaOS terminal · ${session.shell}\x1b[0m`);
        unlisten = await listen<OutputEvent>('terminal://output', ({ payload }) => { if (payload.sessionId === session.sessionId) terminal.write(decodeBase64(payload.data)); });
      } catch (cause) { setError(cause instanceof Error ? cause.message : 'Terminal unavailable.'); }
    };
    void start();
    const input = terminal.onData((data) => { if (sessionRef.current) void invoke('terminal_write', { request: { sessionId: sessionRef.current, data } }); });
    return () => { input.dispose(); resize.disconnect(); unlisten?.(); if (sessionRef.current) void invoke('terminal_kill', { request: { sessionId: sessionRef.current } }); terminal.dispose(); };
  }, [projectRootRef]);

  const interrupt = () => {
    if (!sessionRef.current) return;
    void invoke('terminal_interrupt', { request: { sessionId: sessionRef.current } })
      .catch((cause) => setError(cause instanceof Error ? cause.message : 'Terminal interrupt failed.'));
  };

  return <section className="terminal-view native-terminal-surface" aria-label="Governed terminal"><header><strong>Terminal</strong><button type="button" onClick={interrupt}>Interrupt</button><button type="button" onClick={onClose}>Close</button></header><p className="ps-muted">User PTY · {projectRootRef ? `registered project root (${projectRootDisplayName || 'project'})` : 'verified ImperaOS runtime workspace'} · agent input denied</p>{error ? <p role="alert">{error}</p> : null}<div className="terminal-host" ref={hostRef} /></section>;
}
