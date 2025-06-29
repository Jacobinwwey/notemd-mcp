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

-	**AI-Powered Content Enrichment**: Automatically processes Markdown content to identify key concepts and create `[[wiki-links]]`, building a deeply interconnected knowledge graph.
-	**Automated Documentation Generation**: Generates comprehensive, structured documentation from a single title or keyword, optionally using web research for context.
-	**Integrated Web Research & Summarization**: Performs web searches using Tavily or DuckDuckGo and uses an LLM to provide concise summaries on any topic.
-	**Knowledge Graph Integrity**: Includes endpoints to automatically update or remove backlinks when files are renamed or deleted, preventing broken links.
-	**Syntax Correction**: Provides a utility to batch-fix common Mermaid.js and LaTeX syntax errors often found in LLM-generated content.
-	**Highly Configurable**: All major features, API keys, file paths, and model parameters are easily managed in a central `config.py` file.
-	**Multi-LLM Support**: Compatible with any OpenAI-compliant API, including local models via LMStudio and Ollama, and cloud providers like DeepSeek, Anthropic, Google, and more.
-	**Interactive API Docs**: Comes with automatically generated, interactive API documentation via Swagger UI.

## How It Works

The server is built on a simple and logical architecture:

-	**`main.py` (API Layer)**: Defines all API endpoints using the **FastAPI** framework. It handles incoming requests, validates data using Pydantic, and calls the appropriate functions from the core logic layer.
-	**`notemd_core.py` (Logic Layer)**: The engine of the application. It contains all the business logic for interacting with LLMs, processing text, performing web searches, and managing files within your knowledge base.
-	**`config.py` (User-Defined Space)**: The central configuration hub. This is where you define your file paths, API keys, and tune the behavior of the server to fit your needs.
-	**`cli.js` (MCP Bridge)**: A Node.js-based command-line interface that acts as a bridge to the Python server. It uses the `@modelcontextprotocol/sdk` to create a server that can be called by other tools. It starts the FastAPI server and then communicates with it via HTTP requests.

## Getting Started

Follow these steps to get the Notemd MCP server up and running on your local machine.

### Prerequisites

-	**For Python execution**: Python 3.8+ and `pip` or `uv`.
-	**For NPX execution**: Node.js and `npx`.

### Installation & Running

Choose the method that best fits your workflow.

#### Method 1: Using `npx` (Recommended for Quick Start)

This is the simplest way to start the server. `npx` will temporarily download and run the package. This method now supports **stdio mode**, meaning you will see the FastAPI server logs directly in your terminal.

```bash
# This single command will download the package and start the server.
npx notemd-mcp-server
```

#### Method 2: Local Installation with `uv` or `pip`

This method is for users who want to clone the repository and manage the files locally.

1.	**Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/notemd-mcp.git
    cd notemd-mcp
    ```

2.	**Install dependencies:**
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

3.	**Run the server:**
    ```bash
    uvicorn main:app --reload
    ```

#### Method 3: MCP Configuration

To integrate Notemd MCP with your Mission Control Platform (MCP) setup, add the following to the `mcpServers` object in your `settings.json` file:

```json
 {
   "mcpServers": {
     "notemd-mcp": {
       "description": "Notemd MCP Server - AI-powered text processing and knowledge management
 for your Markdown files.",
       "command": "npx",
       "args": [
         "-y",
         "notemd-mcp-server"
       ],
       "env": {
         "OPENAI_API_KEY": "your_openai_api_key_here",
         "DEEPSEEK_API_KEY": "your_deepseek_api_key_here"
       }
     }
   }
 }
```


## Usage

The best way to explore and interact with the API is through the automatically generated documentation.

-	**Navigate to `http://127.0.0.1:8000/docs`** in your web browser.

You will see a complete, interactive Swagger UI where you can view details for each endpoint, see request models, and even send test requests directly from your browser.

## API Endpoints

| Endpoint | Method | Description | Request Body | Response |
| --- | --- | --- | --- | --- |
| `/process_content` | `POST` | Takes a block of text and enriches it with `[[wiki-links]]`. | `{"content": "string", "cancelled": "boolean"}` | `{"processed_content": "string"}` |
| `/generate_title` | `POST` | Generates full documentation from a single title. | `{"title": "string", "cancelled": "boolean"}` | `{"generated_content": "string"}` |
| `/research_summarize` | `POST` | Performs a web search on a topic and returns an AI-generated summary. | `{"topic": "string", "cancelled": "boolean"}` | `{"summary": "string"}` |
| `/execute_custom_prompt` | `POST` | Execute a user-defined prompt with given content. | `{"prompt": "string", "content": "string", "cancelled": "boolean"}` | `{"response": "string"}` |
| `/handle_file_rename` | `POST` | Updates all backlinks in the vault when a file is renamed. | `{"old_path": "string", "new_path": "string"}` | `{"status": "success"}` |
| `/handle_file_delete` | `POST` | Removes all backlinks to a file that has been deleted. | `{"path": "string"}` | `{"status": "success"}` |
| `/batch_fix_mermaid` | `POST` | Scans a folder and corrects common Mermaid.js and LaTeX syntax errors in `.md` files. | `{"folder_path": "string"}` | `{"errors": [], "modified_count": "integer"}` |
| `/health` | `GET` | A simple health check to confirm the server is running. | (None) | `{"status": "ok"}` |

## Configuration

All configuration is handled in the `config.py` file. Here you can set API keys, file paths, and other settings.

### Core Settings

The `notemd_core.set_settings` function in `main.py` initializes the core functionalities of the server using the following parameters, primarily sourced from `config.py`:

-   `DEFAULT_PROVIDERS`: A list of dictionaries, each defining an LLM provider with its `name`, `apiKey`, `baseUrl`, `model`, `temperature`, and optional `apiVersion` (for Azure OpenAI).
-   `ACTIVE_PROVIDER`: The name of the LLM provider to be used by default for all operations.
-   `CHUNK_WORD_COUNT`: The maximum number of words per chunk when processing content for wiki-linking.
-   `MAX_TOKENS`: The maximum number of tokens allowed for LLM interactions.
-   `ENABLE_DUPLICATE_DETECTION`: Boolean to enable/disable duplicate concept detection during wiki-linking.

### File Paths Configuration

These settings define the directory structure for your knowledge base and logs:

-   `VAULT_ROOT`: The absolute path to your Obsidian vault or the root directory of your Markdown files.
-   `CONCEPT_NOTE_FOLDER`: The subfolder within `VAULT_ROOT` where generated concept notes will be stored.
-   `PROCESSED_FILE_FOLDER`: The subfolder where processed Markdown files will be moved.
-   `CONCEPT_LOG_FOLDER`: The subfolder for storing concept generation logs.
-   `CONCEPT_LOG_FILE_NAME`: The name of the log file for concept generation.

### Search Configuration

Settings related to web research and summarization:

-   `TAVILY_API_KEY`: Your API key for Tavily, if `SEARCH_PROVIDER` is set to "tavily".
-   `SEARCH_PROVIDER`: Specifies the web search engine to use ("tavily" or "duckduckgo").
-   `DDG_MAX_RESULTS`: Maximum number of results to fetch from DuckDuckGo.
-   `DDG_FETCH_TIMEOUT`: Timeout in seconds for DuckDuckGo searches.
-   `MAX_RESEARCH_CONTENT_TOKENS`: Maximum tokens for content used in research.
-   `ENABLE_RESEARCH_IN_GENERATE_CONTENT`: Boolean to enable/disable web research when generating content from a title.
-   `TAVILY_MAX_RESULTS`: Maximum number of results to fetch from Tavily.
-   `TAVILY_SEARCH_DEPTH`: Search depth for Tavily ("basic" or "advanced").

### Stable API Call Settings

These settings control the retry mechanism for LLM API calls:

-   `ENABLE_STABLE_API_CALL`: Boolean to enable/disable stable API calls with retries.
-   `API_CALL_INTERVAL`: Interval in seconds between API call retries.
-   `API_CALL_MAX_RETRIES`: Maximum number of retries for a failed API call.

### Multi-Model and Task-Specific Settings

These settings allow for fine-grained control over which LLM provider and model are used for specific tasks:

-   `ADD_LINKS_PROVIDER`: The LLM provider to use for the `process_content` (add links) operation.
-   `RESEARCH_PROVIDER`: The LLM provider to use for the `research_summarize` operation.
-   `GENERATE_TITLE_PROVIDER`: The LLM provider to use for the `generate_title` operation.
-   `ADD_LINKS_MODEL`: Specific model to use for adding links (overrides provider's default if set).
-   `RESEARCH_MODEL`: Specific model to use for research (overrides provider's default if set).
-   `GENERATE_TITLE_MODEL`: Specific model to use for title generation (overrides provider's default if set).

### Post-processing Settings

-   `REMOVE_CODE_FENCES_ON_ADD_LINKS`: Boolean to remove code fences from content after adding links.

### Language Settings

-   `LANGUAGE`: The default language for content processing.
-   `AVAILABLE_LANGUAGES`: A list of supported languages.

### Custom Prompt Settings

These settings allow you to enable and define custom prompts for various operations:

-   `ENABLE_GLOBAL_CUSTOM_PROMPTS`: Boolean to enable/disable the use of custom prompts globally.
-   `CUSTOM_PROMPT_ADD_LINKS`: Custom prompt string for the `process_content` (add links) operation.
-   `CUSTOM_PROMPT_GENERATE_TITLE`: Custom prompt string for the `generate_title` operation.
-   `CUSTOM_PROMPT_RESEARCH_SUMMARIZE`: Custom prompt string for the `research_summarize` operation.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.