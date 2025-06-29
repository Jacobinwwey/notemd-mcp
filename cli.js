#!/usr/bin/env node

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import axios from 'axios';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

// Import MCP SDK components
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema, McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const FASTAPI_PORT = 8000;
const FASTAPI_URL = `http://localhost:${FASTAPI_PORT}`;

const fastapiClient = axios.create({
    baseURL: FASTAPI_URL,
    timeout: 60000, // 60 seconds timeout
});

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

class NotemdMcpServer {
    constructor() {
        this.mcp_server = new Server(
            { name: "notemd-mcp", version: "0.5.0" },
            { capabilities: { tools: {} } }
        );
        this.setupToolHandlers();
    }

    setupToolHandlers() {
        this.mcp_server.setRequestHandler(ListToolsRequestSchema, this._list_tools.bind(this));
        this.mcp_server.setRequestHandler(CallToolRequestSchema, this._call_tool.bind(this));
    }

    async _list_tools() {
        const tools = [
            {
                name: "process_content",
                description: "Process content using Notemd core logic to add wiki-links.",
                inputSchema: {
                    type: "object",
                    properties: {
                        content: { type: "string", description: "The content to process." },
                        cancelled: { type: "boolean", description: "Whether the operation has been cancelled.", default: false }
                    },
                    required: ["content"]
                }
            },
            {
                name: "generate_title",
                description: "Generate content for a given title.",
                inputSchema: {
                    type: "object",
                    properties: {
                        title: { type: "string", description: "The title for which to generate content." },
                        cancelled: { type: "boolean", description: "Whether the operation has been cancelled.", default: false }
                    },
                    required: ["title"]
                }
            },
            {
                name: "research_summarize",
                description: "Perform web research and summarize a topic.",
                inputSchema: {
                    type: "object",
                    properties: {
                        topic: { type: "string", description: "The topic to research and summarize." },
                        cancelled: { type: "boolean", description: "Whether the operation has been cancelled.", default: false }
                    },
                    required: ["topic"]
                }
            },
            {
                name: "execute_custom_prompt",
                description: "Execute a user-defined prompt with given content.",
                inputSchema: {
                    type: "object",
                    properties: {
                        prompt: { type: "string", description: "The custom prompt to execute." },
                        content: { type: "string", description: "The content to apply the prompt to." },
                        cancelled: { type: "boolean", description: "Whether the operation has been cancelled.", default: false }
                    },
                    required: ["prompt", "content"]
                }
            },
            {
                name: "handle_file_rename",
                description: "Update backlinks when a file is renamed.",
                inputSchema: {
                    type: "object",
                    properties: {
                        old_path: { type: "string", description: "The old path of the renamed file." },
                        new_path: { type: "string", description: "The new path of the renamed file." }
                    },
                    required: ["old_path", "new_path"]
                }
            },
            {
                name: "handle_file_delete",
                description: "Remove backlinks when a file is deleted.",
                inputSchema: {
                    type: "object",
                    properties: {
                        path: { type: "string", description: "The path of the deleted file." }
                    },
                    required: ["path"]
                }
            },
            {
                name: "batch_fix_mermaid",
                description: "Fix Mermaid and LaTeX syntax in all Markdown files in a folder.",
                inputSchema: {
                    type: "object",
                    properties: {
                        folder_path: { type: "string", description: "The path to the folder containing Markdown files." }
                    },
                    required: ["folder_path"]
                }
            }
        ];
        return { tools };
    }

    async _call_tool(request) {
        const tool_name = request.params.name;
        const args = request.params.arguments;
        let responseData;

        try {
            switch (tool_name) {
                case "process_content":
                    responseData = await fastapiClient.post('/process_content', args);
                    return { content: [{ type: "text", text: responseData.data.processed_content }] };
                case "generate_title":
                    responseData = await fastapiClient.post('/generate_title', args);
                    return { content: [{ type: "text", text: responseData.data.generated_content }] };
                case "research_summarize":
                    responseData = await fastapiClient.post('/research_summarize', args);
                    return { content: [{ type: "text", text: responseData.data.summary }] };
                case "execute_custom_prompt":
                    responseData = await fastapiClient.post('/execute_custom_prompt', args);
                    return { content: [{ type: "text", text: responseData.data.response }] };
                case "handle_file_rename":
                    responseData = await fastapiClient.post('/handle_file_rename', args);
                    return { content: [{ type: "text", text: responseData.data.status }] };
                case "handle_file_delete":
                    responseData = await fastapiClient.post('/handle_file_delete', args);
                    return { content: [{ type: "text", text: responseData.data.status }] };
                case "batch_fix_mermaid":
                    responseData = await fastapiClient.post('/batch_fix_mermaid', args);
                    return { content: [{ type: "text", text: JSON.stringify(responseData.data) }] };
                default:
                    throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${tool_name}`);
            }
        } catch (error) {
            console.error(`Error calling FastAPI endpoint for tool ${tool_name}:`, error.message);
            if (error.response) {
                console.error("FastAPI Error Response:", error.response.data);
                throw new McpError(ErrorCode.InternalError, `FastAPI error: ${error.response.data.detail || error.message}`);
            } else if (error.request) {
                throw new McpError(ErrorCode.InternalError, `No response from FastAPI: ${error.message}`);
            } else {
                throw new McpError(ErrorCode.InternalError, `Error setting up request: ${error.message}`);
            }
        }
    }

    async run() {
        const transport = new StdioServerTransport();
        await this.mcp_server.connect(transport);
    }
}

async function main() {
    const argv = yargs(hideBin(process.argv)).option('config', {
        alias: 'c',
        type: 'string',
        description: 'Base64 encoded JSON configuration for the server'
    }).argv;

    try {
        console.error('Verifying Python installation...');
        await runCommand('python', ['--version']);
        console.error('Python is available.');

        console.error('Verifying pip installation...');
        await runCommand('python', ['-m', 'pip', '--version']);
        console.error('pip is available.');

        const requirementsPath = path.join(__dirname, 'requirements.txt');
        console.error(`Installing dependencies from ${requirementsPath}...`);
        await runCommand('python', ['-m', 'pip', 'install', '-r', requirementsPath]);
        console.error('Dependencies installed successfully.');

        // Set environment variable for the Python process
        const env = { ...process.env };
        if (argv.config) {
            env.NOTEMD_CONFIG = argv.config;
        }

        // Start FastAPI server in the background
        const mainPyModule = 'main:app';
        const fastapiProcess = spawn('python', ['-m', 'uvicorn', mainPyModule, '--host', '0.0.0.0', '--port', FASTAPI_PORT.toString()], { cwd: __dirname, stdio: 'inherit', env });

        fastapiProcess.on('close', (code) => {
            if (code !== 0) {
                process.exit(1);
            }
        });

        // Wait for FastAPI to start
        let fastapiReady = false;
        let attempts = 0;
        const maxAttempts = 15; // Increased attempts
        while (!fastapiReady && attempts < maxAttempts) {
            try {
                await fastapiClient.get('/health');
                fastapiReady = true;
                console.error('FastAPI server is ready.');
            } catch (err) {
                console.error(`Waiting for FastAPI server... (attempt ${attempts + 1}/${maxAttempts})`);
                await new Promise(resolve => setTimeout(resolve, 2000));
                attempts++;
            }
        }

        if (!fastapiReady) {
            throw new Error('FastAPI server did not start in time.');
        }

        // Start MCP server
        const mcpServer = new NotemdMcpServer();
        await mcpServer.run();

    } catch (error) {
        console.error('Failed to start the Notemd MCP server:', error.message);
        console.error('Please ensure that Python and pip are installed and available in your system\'s PATH.');
        process.exit(1);
    }
}

main();