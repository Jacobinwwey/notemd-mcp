import { spawn } from 'node:child_process';

/** MCP owns stdout. All child output belongs to the diagnostic channel. */
export function spawnLoggedProcess(command, args, options = {}) {
    const child = spawn(command, args, { ...options, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    child.stdout.pipe(process.stderr, { end: false });
    child.stderr.pipe(process.stderr, { end: false });
    return child;
}
