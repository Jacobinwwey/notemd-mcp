#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

function runCommand(command, args, options = {}) {
    return new Promise((resolve, reject) => {
        const proc = spawn(command, args, { stdio: 'inherit', ...options });
        proc.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Command failed with exit code ${code}: ${command} ${args.join(' ')}`));
            } else {
                resolve();
            }
        });
        proc.on('error', (err) => {
            reject(err);
        });
    });
}

async function main() {
    try {
        console.log('Verifying Python installation...');
        await runCommand('python', ['--version']);
        console.log('Python is available.');

        console.log('Verifying pip installation...');
        await runCommand('python', ['-m', 'pip', '--version']);
        console.log('pip is available.');

        const requirementsPath = path.join(__dirname, 'requirements.txt');
        console.log(`Installing dependencies from ${requirementsPath}...`);
        await runCommand('python', ['-m', 'pip', 'install', '-r', requirementsPath]);
        console.log('Dependencies installed successfully.');

        console.log('Starting Notemd MCP server with Uvicorn...');
        const mainPyPath = path.join(__dirname, 'main:app');
        await runCommand('python', ['-m', 'uvicorn', mainPyPath, '--host', '0.0.0.0', '--port', '8000']);

    } catch (error) {
        console.error('Failed to start the Notemd MCP server:', error.message);
        console.error('Please ensure that Python and pip are installed and available in your system\'s PATH.');
        process.exit(1);
    }
}

main();
