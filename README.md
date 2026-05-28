# Mini Tool Agent

[English](README_en.md) | 简体中文

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-API-green) ![Pydantic](https://img.shields.io/badge/Pydantic-v2-orange) ![pytest](https://img.shields.io/badge/tests-pytest-informational) ![Docker](https://img.shields.io/badge/Docker-ready-2496ED) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

Mini Tool Agent 是一个面向 AI Agent 学习的最小工程项目。它从 LLM API、对话结构、结构化输出、工具调用、Agent Loop 开始，逐步扩展到 FastAPI 服务化、测试、Mock、覆盖率、结构化日志、配置管理和 Docker。

## Introduction

这个项目不是单一示例脚本，而是一套围绕“最小工具型 Agent”展开的学习工程。

它包含两部分：

1. **主应用工程**：位于 `app/`，实现一个可运行的 FastAPI Agent 服务。
2. **学习材料与练习**：位于 `documents/` 和 `exercise/`，覆盖模块 1 的 7 个子模块。你可以在`exercise/`中获取每个子模块的独立自述文档。

主应用支持：

- `GET /health`：服务健康检查。
- `GET /tools`：查看工具列表和参数 schema。
- `POST /chat`：普通 Agent 对话。
- `POST /chat/stream`：SSE streaming 对话。
- 工具调用：计算器、文件搜索、网页摘要 mock、待办事项。
- 结构化日志：记录 trace id、工具选择、工具参数、耗时、错误和最终状态。
- 测试体系：工具层、Agent 层、API 层、配置层测试。

## Project Structure

```text
mini-tool-agent/
  app/
    main.py
    api/
      dependencies.py
      routes.py
      schemas.py
    agent/
      loop.py
      models.py
      prompts.py
    core/
      config.py
      errors.py
      logging.py
      trace.py
    tools/
      base.py
      registry.py
      settings.py
      calculator.py
      file_search.py
      web_summary_mock.py
      todo.py
  documents/
    模块1_LLM工程基础与最小Agent_详细学习路线.md
    子模块*_概念教学.md
  exercise/
    submodule_1_exercise.py
    submodule_2_exercise.py
    submodule_3_exercise.py
    submodule_4_exercise/
    README_submodule_5_exercise.md
    README_submodule_6_exercise.md
    README_submodule_7_exercise.md
  tests/
  Dockerfile
  docker-compose.yml
  .env.example
  pyproject.toml
```

## Learning Modules

| 子模块 | 内容 | 产出 |
|---|---|---|
| 1 | LLM API 与对话结构 | API 调用与 messages 练习 |
| 2 | Structured Output 与 Pydantic 校验 | 结构化输出解析练习 |
| 3 | Tool Calling 与工具层设计 | 工具抽象与安全计算器 |
| 4 | 手写最小 Agent Loop | 多文件 Agent Loop 练习 |
| 5 | FastAPI 服务化 | 完整后端工程骨架 |
| 6 | 测试、Mock 与覆盖率 | 20+ 测试与练习题 |
| 7 | 日志、配置、Docker 与 README | 工程交付外壳 |

## Installation

1. 克隆项目并进入目录：

```bash
git clone https://github.com/lWaterLite/mini-tool-agent
cd mini-tool-agent
```

2. 安装依赖：

```bash
uv sync
```

如果你不使用 `uv`，也可以使用：

```bash
python -m pip install -e .
```

3. 创建本地环境变量文件：

```powershell
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

> Important: `.env` 中可能包含 API key，不要提交到 Git。当前主工程使用规则型 mock planner，不需要真实 LLM API key 也可以运行大部分功能和测试。

## Usage

### 启动 API 服务

```bash
uvicorn app.main:app --reload
```

或使用项目虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

### 健康检查

```bash
curl http://127.0.0.1:8000/health
```

### 查看工具

```bash
curl http://127.0.0.1:8000/tools
```

### 普通对话

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"你好"}'
```

### 调用计算器工具

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"计算 3 * (4 + 5)"}'
```

### Streaming

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"计算 1 + 2"}'
```

## Tools

| 工具 | 作用 | 说明 |
|---|---|---|
| `calculator` | 安全数学计算 | 使用 AST 白名单，不直接使用 `eval` |
| `file_search` | 文件搜索 | 在限定目录中搜索文本 |
| `web_summary_mock` | 网页摘要 mock | 不访问真实网络，便于稳定测试 |
| `todo` | 待办事项 | 内存存储，支持 `session_id` 隔离 |

## Configuration

配置示例位于 `.env.example`。

常用配置：

```env
APP_NAME=mini-tool-agent
APP_ENV=development
LOG_LEVEL=INFO
FILE_SEARCH_ROOT=documents
MAX_FILE_SEARCH_RESULTS=5
MAX_AGENT_STEPS=4
AGENT_PLANNER_MODE=mock
CALCULATOR_MAX_POWER_EXPONENT=8
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4o-mini
```

`AGENT_PLANNER_MODE=mock` 会使用规则型 mock planner，不调用真实模型。

`AGENT_PLANNER_MODE=llm` 会使用 OpenAI 兼容接口生成工具计划，需要配置 `LLM_API_KEY` 或 `OPENAI_API_KEY`。

配置入口在：

```text
app/core/config.py
```

## Testing

运行全部测试：

```bash
pytest
```

或：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

运行覆盖率：

```bash
pytest --cov=app --cov-report=term-missing
```

当前测试覆盖：

- 工具单元测试。
- Agent Loop 测试。
- API 测试。
- Prompt 构造测试。
- 配置读取测试。
- streaming 错误事件测试。

## Docker

构建镜像：

```bash
docker build -t mini-tool-agent .
```

运行容器：

```bash
docker run --env-file .env -p 8000:8000 mini-tool-agent
```

使用 Docker Compose：

```bash
docker compose up --build
```

## Logging

项目使用结构化日志记录 Agent 请求流程。

一次工具调用通常包含：

```text
request_started
agent_plan_created
tool_call_started
tool_call_finished
request_finished
```

失败时会记录：

```text
tool_call_failed
request_finished
```

关键字段包括：

- `trace_id`
- `message_preview`
- `planned_tools`
- `tool_name`
- `tool_arguments`
- `latency_ms`
- `error_code`
- `final_status`

## License

[MIT](LICENSE) @ 2026 lWaterLite
