import { spawn } from 'node:child_process';

const child = spawn('corepack', ['pnpm', 'dev', '--host', '127.0.0.1'], {
  env: {
    ...process.env,
    VITE_OPERATOR_PANEL_PREVIEW: '1',
  },
  shell: process.platform === 'win32',
  stdio: 'inherit',
});

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
