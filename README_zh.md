# Notemd MCP (任务控制平台) 服务器

```
==================================================
  _   _       _   _ ___    __  __ ___
 | \ | | ___ | |_| |___|  |  \/  |___ \
 |  \| |/ _ \| __| |___|  | |\/| |   | |
 | |\  | (_) | |_| |___   | |  | |___| |
 |_| \_|\___/ \__|_|___|  |_|  |_|____/
==================================================
    由 AI 驱动的您的知识库后端
==================================================
```

欢迎使用 Notemd MCP 服务器！本项目提供了一个强大的、独立的后端服务器，通过 Web API 实现了 [Notemd Obsidian 插件](https://github.com/Jacobinwwey/obsidian-NotEMD) 的核心 AI 文本处理和知识管理功能。

该服务器使用 Python 和 FastAPI 构建，允许您将繁重的计算任务（如 LLM 调用和文件处理）从 Obsidian 客户端中卸载出来，并提供了一个强大的 API 以编程方式与您的知识库进行交互。

[English](./README.md) | [简体中文](./README_zh.md)

## 功能特性

-   **AI 驱动的内容增强**：自动处理 Markdown 内容，识别核心概念并创建 `[[维基链接]]`，构建一个深度互联的个人知识图谱。
-   **自动化文档生成**：从单个标题或关键字生成全面、结构化的文档，并可选择使用网络研究来为生成提供更丰富的上下文。
-   **集成的网络研究与摘要**：使用 Tavily 或 DuckDuckGo 执行网络搜索，并利用 LLM 为任何主题提供简洁的摘要。
-   **知识图谱完整性**：包含在文件重命名或删除时自动更新或移除反向链接的端点，防止出现死链接。
-   **语法修正**：提供一个实用工具，用于批量修复 LLM 生成内容中常见的 Mermaid.js 和 LaTeX 语法错误。
-   **高度可配置**：所有主要功能、API 密钥、文件路径和模型参数都在一个中央 `config.py` 文件中轻松管理。
-   **多 LLM 支持**：与任何兼容 OpenAI 的 API 兼容，包括通过 LMStudio 和 Ollama 的本地模型，以及像 DeepSeek、Anthropic、Google 等云提供商。
-   **交互式 API 文档**：通过 Swagger UI 自动生成交互式 API 文档。

## 工作原理

该项目基于一个简单而逻辑清晰的架构：

-   **`main.py` (API 层)**：使用 **FastAPI** 框架定义所有 API 端点。它处理传入的请求，使用 Pydantic 验证数据，并调用核心逻辑层的相应函数。
-   **`notemd_core.py` (逻辑层)**：应用程序的引擎。它包含了与 LLM 交互、处理文本、执行网络搜索以及在您的知识库中管理文件的所有业务逻辑。
-   **`config.py` (用户定义空间)**：中央配置中心。您可以在此定义文件路径、API 密钥，并调整服务器的行为以满足您的需求。
-   **`cli.js` (MCP 桥接)**：一个基于 Node.js 的命令行接口，作为 Python 服务器的桥梁。它使用 `@modelcontextprotocol/sdk` 创建一个服务器，该服务器可以被其他工具调用。它启动 FastAPI 服务器，然后通过 HTTP 请求与其通信。

## 快速上手

请按照以下步骤在您的本地计算机上安装并运行 Notemd MCP 服务器。

### 先决条件

-   **对于 Python 执行**：Python 3.8+ 和 `pip` 或 `uv`。
-   **对于 NPX 执行**：Node.js 和 `npx`。

### 安装与运行

选择最适合您工作流程的方法。

#### 方法一：使用 `npx` (推荐用于快速启动)

这是启动服务器最简单的方法。`npx` 将临时下载并运行该包。

```bash
# 这条命令将下载包并启动服务器。
npx notemd-mcp-server
```

#### 方法二：使用 `uv` 或 `pip` 进行本地安装

此方法适用于希望克隆代码仓库并在本地管理文件的用户。

1.  **克隆代码仓库：**
    ```bash
    git clone https://github.com/your-repo/notemd-mcp.git
    cd notemd-mcp
    ```

2.  **安装依赖项：**
    *   **使用 `uv` (推荐):**
        ```bash
        uv venv
        uv pip install -r requirements.txt
        ```
    *   **使用 `pip`:**
        ```bash
        python -m venv .venv
        # 激活环境 (例如, source .venv/bin/activate)
        pip install -r requirements.txt
        ```

3.  **运行服务器：**
    ```bash
    uvicorn main:app --reload
    ```

#### 方法三：MCP 配置

要将 Notemd MCP 与您的任务控制平台 (MCP) 设置集成，请将以下内容添加到 `settings.json` 文件中的 `mcpServers` 对象：

```json
 {
   "mcpServers": {
     "notemd-mcp": {
       "description": "Notemd MCP Server - AI-powered text processing and knowledge management\n for your Markdown files.",
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

## 使用方法

探索和与 API 交互的最佳方式是通过自动生成的文档。

-   **在您的网络浏览器中导航到 `http://127.0.0.1:8000/docs`**

您将看到一个完整的、交互式的 Swagger UI，您可以在其中查看每个端点的详细信息、请求模型，甚至直接从浏览器发送测试请求。

## API 端点

| 端点 | 方法 | 描述 | 请求体 | 响应 |
| --- | --- | --- | --- | --- |
| `/process_content` | `POST` | 接收一段文本并通过添加 `[[维基链接]]` 来丰富它。 | `{"content": "string", "cancelled": "boolean"}` | `{"processed_content": "string"}` |
| `/generate_title` | `POST` | 从单个标题生成完整的文档。 | `{"title": "string", "cancelled": "boolean"}` | `{"generated_content": "string"}` |
| `/research_summarize` | `POST` | 对一个主题进行网络搜索，并返回一个由 AI 生成的摘要。 | `{"topic": "string", "cancelled": "boolean"}` | `{"summary": "string"}` |
| `/execute_custom_prompt` | `POST` | 执行用户定义的提示与给定内容。 | `{"prompt": "string", "content": "string", "cancelled": "boolean"}` | `{"response": "string"}` |
| `/handle_file_rename` | `POST` | 当文件被重命名时，更新 vault 中的所有反向链接。 | `{"old_path": "string", "new_path": "string"}` | `{"status": "success"}` |
| `/handle_file_delete` | `POST` | 当文件被删除时，移除所有指向该文件的反向链接。 | `{"path": "string"}` | `{"status": "success"}` |
| `/batch_fix_mermaid` | `POST` | 扫描一个文件夹并修正 `.md` 文件中常见的 Mermaid.js 和 LaTeX 语法错误。 | `{"folder_path": "string"}` | `{"errors": [], "modified_count": "integer"}` |
| `/health` | `GET` | 一个简单的健康检查，以确认服务器正在运行。 | (None) | `{"status": "ok"}` |

## 配置

所有配置都在 `config.py` 文件中处理。您可以在此处设置 API 密钥、文件路径和其他设置。

### 核心设置

`main.py` 中的 `notemd_core.set_settings` 函数使用以下参数初始化服务器的核心功能，这些参数主要来源于 `config.py`：

-   `DEFAULT_PROVIDERS`：一个字典列表，每个字典定义一个 LLM 提供商，包含其 `name`、`apiKey`、`baseUrl`、`model`、`temperature` 和可选的 `apiVersion`（用于 Azure OpenAI）。
-   `ACTIVE_PROVIDER`：默认用于所有操作的 LLM 提供商的名称。
-   `CHUNK_WORD_COUNT`：在处理内容以进行维基链接时，每个块的最大单词数。
-   `MAX_TOKENS`：LLM 交互允许的最大令牌数。
-   `ENABLE_DUPLICATE_DETECTION`：布尔值，用于在维基链接期间启用/禁用重复概念检测。

### 文件路径配置

这些设置定义了您的知识库和日志的目录结构：

-   `VAULT_ROOT`：您的 Obsidian vault 或 Markdown 文件根目录的绝对路径。
-   `CONCEPT_NOTE_FOLDER`：`VAULT_ROOT` 中用于存储生成的概念笔记的子文件夹。
-   `PROCESSED_FILE_FOLDER`：用于移动已处理的 Markdown 文件的子文件夹。
-   `CONCEPT_LOG_FOLDER`：用于存储概念生成日志的子文件夹。
-   `CONCEPT_LOG_FILE_NAME`：概念生成日志文件的名称。

### 搜索配置

与网络研究和摘要相关的设置：

-   `TAVILY_API_KEY`：如果 `SEARCH_PROVIDER` 设置为 "tavily"，则为您的 Tavily API 密钥。
-   `SEARCH_PROVIDER`：指定要使用的网络搜索引擎（"tavily" 或 "duckduckgo"）。
-   `DDG_MAX_RESULTS`：从 DuckDuckGo 获取的最大结果数。
-   `DDG_FETCH_TIMEOUT`：DuckDuckGo 搜索的超时时间（秒）。
-   `MAX_RESEARCH_CONTENT_TOKENS`：研究中使用的内容的最大令牌数。
-   `ENABLE_RESEARCH_IN_GENERATE_CONTENT`：布尔值，用于在从标题生成内容时启用/禁用网络研究。
-   `TAVILY_MAX_RESULTS`：从 Tavily 获取的最大结果数。
-   `TAVILY_SEARCH_DEPTH`：Tavily 的搜索深度（"basic" 或 "advanced"）。

### 稳定 API 调用设置

这些设置控制 LLM API 调用的重试机制：

-   `ENABLE_STABLE_API_CALL`：布尔值，用于启用/禁用带重试的稳定 API 调用。
-   `API_CALL_INTERVAL`：API 调用重试之间的时间间隔（秒）。
-   `API_CALL_MAX_RETRIES`：失败 API 调用的最大重试次数。

### 多模型和任务特定设置

这些设置允许对特定任务使用哪个 LLM 提供商和模型进行细粒度控制：

-   `ADD_LINKS_PROVIDER`：用于 `process_content`（添加链接）操作的 LLM 提供商。
-   `RESEARCH_PROVIDER`：用于 `research_summarize` 操作的 LLM 提供商。
-   `GENERATE_TITLE_PROVIDER`：用于 `generate_title` 操作的 LLM 提供商。
-   `ADD_LINKS_MODEL`：用于添加链接的特定模型（如果设置，则覆盖提供商的默认值）。
-   `RESEARCH_MODEL`：用于研究的特定模型（如果设置，则覆盖提供商的默认值）。
-   `GENERATE_TITLE_MODEL`：用于标题生成的特定模型（如果设置，则覆盖提供商的默认值）。

### 后处理设置

-   `REMOVE_CODE_FENCES_ON_ADD_LINKS`：布尔值，用于在添加链接后从内容中删除代码围栏。

### 语言设置

-   `LANGUAGE`：内容处理的默认语言。
-   `AVAILABLE_LANGUAGES`：支持的语言列表。

### 自定义提示设置

这些设置允许您启用和定义各种操作的自定义提示：

-   `ENABLE_GLOBAL_CUSTOM_PROMPTS`：布尔值，用于全局启用/禁用自定义提示。
-   `CUSTOM_PROMPT_ADD_LINKS`：`process_content`（添加链接）操作的自定义提示字符串。
-   `CUSTOM_PROMPT_GENERATE_TITLE`：`generate_title` 操作的自定义提示字符串。
-   `CUSTOM_PROMPT_RESEARCH_SUMMARIZE`：`research_summarize` 操作的自定义提示字符串。

## 配置

所有配置都在 `config.py` 文件中处理。您可以在此处设置 API 密钥、文件路径和其他设置。

### 核心设置

`main.py` 中的 `notemd_core.set_settings` 函数使用以下参数初始化服务器的核心功能，这些参数主要来源于 `config.py`：

-   `DEFAULT_PROVIDERS`：一个字典列表，每个字典定义一个 LLM 提供商，包含其 `name`、`apiKey`、`baseUrl`、`model`、`temperature` 和可选的 `apiVersion`（用于 Azure OpenAI）。
-   `ACTIVE_PROVIDER`：默认用于所有操作的 LLM 提供商的名称。
-   `CHUNK_WORD_COUNT`：在处理内容以进行维基链接时，每个块的最大单词数。
-   `MAX_TOKENS`：LLM 交互允许的最大令牌数。
-   `ENABLE_DUPLICATE_DETECTION`：布尔值，用于在维基链接期间启用/禁用重复概念检测。

### 文件路径配置

这些设置定义了您的知识库和日志的目录结构：

-   `VAULT_ROOT`：您的 Obsidian vault 或 Markdown 文件根目录的绝对路径。
-   `CONCEPT_NOTE_FOLDER`：`VAULT_ROOT` 中用于存储生成的概念笔记的子文件夹。
-   `PROCESSED_FILE_FOLDER`：用于移动已处理的 Markdown 文件的子文件夹。
-   `CONCEPT_LOG_FOLDER`：用于存储概念生成日志的子文件夹。
-   `CONCEPT_LOG_FILE_NAME`：概念生成日志文件的名称。

### 搜索配置

与网络研究和摘要相关的设置：

-   `TAVILY_API_KEY`：如果 `SEARCH_PROVIDER` 设置为 "tavily"，则为您的 Tavily API 密钥。
-   `SEARCH_PROVIDER`：指定要使用的网络搜索引擎（"tavily" 或 "duckduckgo"）。
-   `DDG_MAX_RESULTS`：从 DuckDuckGo 获取的最大结果数。
-   `DDG_FETCH_TIMEOUT`：DuckDuckGo 搜索的超时时间（秒）。
-   `MAX_RESEARCH_CONTENT_TOKENS`：研究中使用的内容的最大令牌数。
-   `ENABLE_RESEARCH_IN_GENERATE_CONTENT`：布尔值，用于在从标题生成内容时启用/禁用网络研究。
-   `TAVILY_MAX_RESULTS`：从 Tavily 获取的最大结果数。
-   `TAVILY_SEARCH_DEPTH`：Tavily 的搜索深度（"basic" 或 "advanced"）。

### 稳定 API 调用设置

这些设置控制 LLM API 调用的重试机制：

-   `ENABLE_STABLE_API_CALL`：布尔值，用于启用/禁用带重试的稳定 API 调用。
-   `API_CALL_INTERVAL`：API 调用重试之间的时间间隔（秒）。
-   `API_CALL_MAX_RETRIES`：失败 API 调用的最大重试次数。

### 多模型和任务特定设置

这些设置允许对特定任务使用哪个 LLM 提供商和模型进行细粒度控制：

-   `ADD_LINKS_PROVIDER`：用于 `process_content`（添加链接）操作的 LLM 提供商。
-   `RESEARCH_PROVIDER`：用于 `research_summarize` 操作的 LLM 提供商。
-   `GENERATE_TITLE_PROVIDER`：用于 `generate_title` 操作的 LLM 提供商。
-   `ADD_LINKS_MODEL`：用于添加链接的特定模型（如果设置，则覆盖提供商的默认值）。
-   `RESEARCH_MODEL`：用于研究的特定模型（如果设置，则覆盖提供商的默认值）。
-   `GENERATE_TITLE_MODEL`：用于标题生成的特定模型（如果设置，则覆盖提供商的默认值）。

### 后处理设置

-   `REMOVE_CODE_FENCES_ON_ADD_LINKS`：布尔值，用于在添加链接后从内容中删除代码围栏。

### 语言设置

-   `LANGUAGE`：内容处理的默认语言。
-   `AVAILABLE_LANGUAGES`：支持的语言列表。

### 自定义提示设置

这些设置允许您启用和定义各种操作的自定义提示：

-   `ENABLE_GLOBAL_CUSTOM_PROMPTS`：布尔值，用于全局启用/禁用自定义提示。
-   `CUSTOM_PROMPT_ADD_LINKS`：`process_content`（添加链接）操作的自定义提示字符串。
-   `CUSTOM_PROMPT_GENERATE_TITLE`：`generate_title` 操作的自定义提示字符串。
-   `CUSTOM_PROMPT_RESEARCH_SUMMARIZE`：`research_summarize` 操作的自定义提示字符串。


## 许可证

本项目根据 MIT 许可证授权。有关详细信息，请参阅 `LICENSE` 文件。

