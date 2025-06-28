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

#### 方法二：使用 `uvx` (基于 Python 的快速启动)

`uvx` 是 `uv` 的 `npx` 等效物，允许远程执行 Python 包。

```bash
# 此命令将在隔离环境中临时安装并运行服务器。
uvx notemd-mcp-server
```

#### 方法三：使用 `uv` 或 `pip` 进行本地安装

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

### 方法四：通过 MCP 配置自动安装

对于高级用户和工具开发者，`notemd-mcp` 服务器支持通过配置文件进行自动发现和安装。

1.  **发现服务器**：其他工具可以读取本代码仓库中的 `mcp_servers.json` 文件，以找到服务器的安装命令。

2.  **执行命令**：然后，该工具可以执行 JSON 文件中指定的命令来启动服务器。例如，一个工具可以从 `mcp_servers.json` 中解析出以下内容：

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

    然后，该工具将执行 `npx -y notemd-mcp-server` 来启动服务器。

此方法允许与其他开发工具和 CLI 无缝集成，使它们能够作为依赖项来启动和管理 `notemd-mcp` 服务器。

## 使用方法

探索和与 API 交互的最佳方式是通过自动生成的文档。

-   **在您的网络浏览器中导航到 `http://127.0.0.1:8000/docs`**

您将看到一个完整的、交互式的 Swagger UI，您可以在其中查看每个端点的详细信息、请求模型，甚至直接从浏览器发送测试请求。

## API 端点

| 端点                          | 方法   | 描述                                                                        |
| ----------------------------- | ------ | --------------------------------------------------------------------------- |
| `/process_content`            | `POST` | 接收一段文本并通过添加 `[[维基链接]]` 来丰富它。                            |
| `/generate_title`             | `POST` | 从单个标题生成完整的文档。                                                  |
| `/research_summarize`         | `POST` | 对一个主题进行网络搜索，并返回一个由 AI 生成的摘要。                        |
| `/handle_file_rename`         | `POST` | 当文件被重命名时，更新 vault 中的所有反向链接。                             |
| `/handle_file_delete`         | `POST` | 当文件被删除时，移除所有指向该文件的反向链接。                              |
| `/batch_fix_mermaid`          | `POST` | 扫描一个文件夹并修正 `.md` 文件中常见的 Mermaid.js 和 LaTeX 语法错误。      |
| `/health`                     | `GET`  | 一个简单的健康检查，以确认服务器正在运行。                                  |

## 许可证

本项目根据 MIT 许可证授权。有关详细信息，请参阅 `LICENSE` 文件。

