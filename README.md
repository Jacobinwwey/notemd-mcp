# Notemd MCP (Mission Control Platform) Server

```
==================================================
  _   _       _   _ ___    __  __ ___
 | \ | | ___ | |_| |___|  |  \/  |___ \
 |  \| |/ _ \| __| |___|  | |\/| |   | |
 | |\  | (_) | |_| |___   | |  | |___| |
 |_| \_|\___/ \__|_|___|  | |  | |____/
==================================================
   AI-Powered Backend for Your Knowledge Base
==================================================
```

Welcome to the Notemd MCP Server! This project provides a powerful, standalone backend server that exposes the core AI-powered text processing and knowledge management functionalities of the [Notemd Obsidian Plugin](https://github.com/Jacobinwwey/obsidian-NotEMD).

[English](./README.md) | [简体中文](./README_zh.md)

Built with Python and FastAPI, this server allows you to offload heavy computational tasks from the client and provides a robust API to interact with your knowledge base programmatically.

## Features

-   **AI-Powered Content Enrichment**: Automatically processes Markdown content to identify key concepts and create `[[wiki-links]]`, building a deeply interconnected knowledge graph.
-   **Automated Documentation Generation**: Generates comprehensive, structured documentation from a single title or keyword, optionally using web research for context.
-   **Integrated Web Research & Summarization**: Performs web searches using Tavily or DuckDuckGo and uses an LLM to provide concise summaries on any topic.
-   **Knowledge Graph Integrity**: Includes endpoints to automatically update or remove backlinks when files are renamed or deleted, preventing broken links.
-   **Syntax Correction**: Provides a utility to batch-fix common Mermaid.js and LaTeX syntax errors often found in LLM-generated content.
-   **Highly Configurable**: All major features, API keys, file paths, and model parameters are easily managed in a central `config.py` file.
-   **Multi-LLM Support**: Compatible with any OpenAI-compliant API, including local models via LMStudio and Ollama, and cloud providers like DeepSeek, Anthropic, Google, and more.
-   **Interactive API Docs**: Comes with automatically generated, interactive API documentation via Swagger UI.

## How It Works

The server is built on a simple and logical architecture:

-   **`main.py` (API Layer)**: Defines all API endpoints using the **FastAPI** framework. It handles incoming requests, validates data using Pydantic, and calls the appropriate functions from the core logic layer.
-   **`notemd_core.py` (Logic Layer)**: The engine of the application. It contains all the business logic for interacting with LLMs, processing text, performing web searches, and managing files within your knowledge base.
-   **`config.py` (User-Defined Space)**: The central configuration hub. This is where you define your file paths, API keys, and tune the behavior of the server to fit your needs.

## Getting Started

Follow these steps to get the Notemd MCP server up and running on your local machine.

### Prerequisites

-   **For Python execution**: Python 3.8+ and `pip` or `uv`.
-   **For NPX execution**: Node.js and `npx`.

### Installation & Running

Choose the method that best fits your workflow.

#### Method 1: Using `npx` (Recommended for Quick Start)

This is the simplest way to start the server. `npx` will temporarily download and run the package.

```bash
# This single command will download the package and start the server.
npx notemd-mcp-server
```

#### Method 2: Using `uvx` (Python-based Quick Start)

`uvx` is the `uv` equivalent of `npx`, allowing for remote execution of Python packages.

```bash
# This command will temporarily install and run the server in an isolated environment.
uvx notemd-mcp-server
```

#### Method 3: Local Installation with `uv` or `pip`

This method is for users who want to clone the repository and manage the files locally.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/notemd-mcp.git
    cd notemd-mcp
    ```

2.  **Install dependencies:**
    *   **Using `uv` (Recommended):**
        ```bash
        uv venv
        uv pip install -r requirements.txt
        ```
    *   **Using `pip`:**
        ```bash
        python -m venv .venv
        # Activate the environment (e.g., source .venv/bin/activate)
        pip install -r requirements.txt
        ```

3.  **Run the server:**
    ```bash
    uvicorn main:app --reload
    ```

### Method 4: Automated Installation via MCP Configuration

For advanced users and tool developers, the `notemd-mcp` server supports automated discovery and installation through a configuration file.

1.  **Discover the Server**: Other tools can read the `mcp_servers.json` file in this repository to find the installation command for the server.

2.  **Execute the Command**: The tool can then execute the command specified in the JSON file to launch the server. For example, a tool could parse the following from `mcp_servers.json`:

    ```json
    {
      "mcpServers": {
        "notemd-mcp": {
          "description": "Notemd MCP Server - AI-powered text processing and knowledge management for your Markdown files.",
          "command": "npx",
          "args": [
            "-y",
            "notemd-mcp-server"
          ]
        }
      }
    }
    ```

    The tool would then execute `npx -y notemd-mcp-server` to start the server.

This method allows for seamless integration with other developer tools and CLIs, enabling them to launch and manage the `notemd-mcp` server as a dependency.


## Usage

The best way to explore and interact with the API is through the automatically generated documentation.

-   **Navigate to `http://127.0.0.1:8000/docs`** in your web browser.

You will see a complete, interactive Swagger UI where you can view details for each endpoint, see request models, and even send test requests directly from your browser.

## API Endpoints

| Endpoint                      | Method | Description                                                                                             |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------------------------- |
| `/process_content`            | `POST` | Takes a block of text and enriches it with `[[wiki-links]]`.                                            |
| `/generate_title`             | `POST` | Generates full documentation from a single title.                                                       |
| `/research_summarize`         | `POST` | Performs a web search on a topic and returns an AI-generated summary.                                     |
| `/handle_file_rename`         | `POST` | Updates all backlinks in the vault when a file is renamed.                                              |
| `/handle_file_delete`         | `POST` | Removes all backlinks to a file that has been deleted.                                                  |
| `/batch_fix_mermaid`          | `POST` | Scans a folder and corrects common Mermaid.js and LaTeX syntax errors in `.md` files.                   |
| `/health`                     | `GET`  | A simple health check to confirm the server is running.                                                 |

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

