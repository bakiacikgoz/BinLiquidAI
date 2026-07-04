import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { assertRouteBridgeCommandParity } from '../src/routeCapabilityBridgeParity';
import { routeCapabilityMatrix } from '../src/routeCapabilityMatrix';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(SCRIPT_DIR, '..');
const LIB_RS_PATH = path.join(APP_ROOT, 'src-tauri', 'src', 'lib.rs');

export function assertBridgeCommandParity(libSource = fs.readFileSync(LIB_RS_PATH, 'utf8')): {
  status: 'passed';
  checkedActions: number;
  registeredCommands: number;
} {
  return assertRouteBridgeCommandParity(routeCapabilityMatrix, libSource);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    console.log(JSON.stringify(assertBridgeCommandParity(), null, 2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
