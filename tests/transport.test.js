import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { NotemdMcpServer } from '../cli.js';
import { ErrorCode } from '@modelcontextprotocol/sdk/types.js';
import { mkdtempSync, symlinkSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

test('tool names and response fields remain compatible; unknown tool keeps protocol code', async () => {
    const calls = [];
    const server = new NotemdMcpServer({ post: async (...args) => { calls.push(args); return { data: { diagram: 'graph TD' } }; } });
    const reply = await server._call_tool({ params: { name: 'generate_experimental_diagram', arguments: { content: 'source' } } });
    assert.equal(reply.content[0].text, 'graph TD');
    assert.equal(calls[0][0], '/generate_experimental_diagram');
    await assert.rejects(server._call_tool({ params: { name: 'missing', arguments: {} } }), error => error.code === ErrorCode.MethodNotFound);
});

test('child stdout and stderr remain visible without polluting protocol stdout', () => {
    const script = String.raw`import { spawnLoggedProcess } from "./process-output.js"; const child=spawnLoggedProcess(process.execPath,["-e","console.log(\"child out\");console.error(\"child err\")"]); child.on("close",()=>console.log(JSON.stringify({jsonrpc:"2.0",id:1,result:{}})));`;
    const run = spawnSync(process.execPath, ['--input-type=module', '-e', script], { cwd: new URL('..', import.meta.url), encoding: 'utf8', timeout: 10000, windowsHide: true });
    assert.equal(run.status, 0, run.stderr);
    assert.equal(JSON.parse(run.stdout).jsonrpc, '2.0');
    assert.match(run.stderr, /child out/);
    assert.match(run.stderr, /child err/);
});

test('backend error bodies are not forwarded as diagnostics', async () => {
    const server = new NotemdMcpServer({ post: async () => { throw { response: { status: 500, data: { detail: 'SECRET_PROVIDER_KEY' } } }; } });
    await assert.rejects(server._call_tool({ params: { name: 'generate_diagram', arguments: {} } }), error => !error.message.includes('SECRET_PROVIDER_KEY') && error.message.includes('500'));
});

test('npm-style symlink entry starts the CLI without starting Python for help', (context) => {
    const directory = mkdtempSync(join(tmpdir(), 'notemd-cli-bin-'));
    try {
        const entry = join(directory, 'notemd-mcp');
        try { symlinkSync(fileURLToPath(new URL('../cli.js', import.meta.url)), entry, 'file'); }
        catch (error) {
            if (process.platform === 'win32' && error.code === 'EPERM') { context.skip('Windows host does not grant symlink creation'); return; }
            throw error;
        }
        const run = spawnSync(process.execPath, [entry, '--help'], { encoding: 'utf8', timeout: 10000, windowsHide: true });
        assert.equal(run.status, 0, run.stderr);
        assert.match(run.stdout, /Base64 encoded JSON configuration/);
        assert.doesNotMatch(run.stderr, /Verifying Python/);
    } finally { rmSync(directory, { recursive: true, force: true }); }
});
