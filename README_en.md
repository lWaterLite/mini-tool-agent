# Mini Tool Agent

English | [简体中文](README.md)

![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-API-green) ![Pydantic](https://img.shields.io/badge/Pydantic-v2-orange) ![pytest](https://img.shields.io/badge/tests-pytest-informational) ![Docker](https://img.shields.io/badge/Docker-ready-2496ED) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

Mini Tool Agent is a learning-oriented AI Agent project. It starts from LLM API basics, conversation structure, structured output, tool calling, and a minimal Agent Loop, then gradually expands into FastAPI service integration, testing, mock design, coverage, structured logging, configuration management, and Docker.

## Introduction

This project is not a single demo script. It is a compact learning project centered around a minimal tool-using Agent.

It contains two main parts:

1. **Main application**: located in `app/`, implementing a runnable FastAPI Agent service.
2. **Learning materials and exercises**: located in `documents/` and `exercise/`, covering all seven submodules of Module 1. You can obtain the independent self-description documents for each submodule in the `exercise/` directory.

The main application supports:

- `GET /health`: service health check.
- `GET /tools`: list available tools and parameter schemas.
- `POST /chat`: normal Agent chat.
- `POST /chat/stream`: SSE streaming chat.
- Tool calls: calculator, file search, mock web summary, and todo management.
- Structured logging: trace id, selected tool, tool arguments, latency, errors, and final status.
- Tests: tool-level, Agent-level, API-level, and configuration tests.

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
    Module 1 learning route and concept notes
  exercise/
    submodule exercises and exercise READMEs
  tests/
  Dockerfile
  docker-compose.yml
  .env.example
  pyproject.toml
```

## Learning Modules

| Submodule | Topic | Output |
|---|---|---|
| 1 | LLM API and conversation structure | API calling and messages practice |
| 2 | Structured Output and Pydantic validation | Structured output parsing |
| 3 | Tool Calling and tool-layer design | Tool abstraction and safe calculator |
| 4 | Minimal handwritten Agent Loop | Multi-file Agent Loop exercise |
| 5 | FastAPI service integration | Full backend service skeleton |
| 6 | Testing, Mock, and coverage | 20+ tests and exercises |
| 7 | Logging, configuration, Docker, and README | Engineering delivery shell |

## Installation

1. Clone the project and enter the directory:

```bash
git clone <your-repo-url>
cd mini-tool-agent
```

2. Install dependencies:

```bash
uv sync
```

If you do not use `uv`, you can also run:

```bash
python -m pip install -e .
```

3. Create a local environment file:

```powershell
copy .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

> Important: `.env` may contain API keys. Do not commit it to Git. The current main application uses a rule-based mock planner, so most features and tests can run without a real LLM API key.

## Usage

### Start the API service

```bash
uvicorn app.main:app --reload
```

Or use the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

### Health check

```bash
curl http://127.0.0.1:8000/health
```

### List tools

```bash
curl http://127.0.0.1:8000/tools
```

### Basic chat

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Calculator tool

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"calculate 3 * (4 + 5)"}'
```

### Streaming

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"calculate 1 + 2"}'
```

## Tools

| Tool | Purpose | Notes |
|---|---|---|
| `calculator` | Safe math calculation | Uses an AST allowlist instead of raw `eval` |
| `file_search` | File search | Searches text under a limited root directory |
| `web_summary_mock` | Mock web summary | Does not access the real network, useful for stable tests |
| `todo` | Todo management | In-memory store with `session_id` isolation |

## Configuration

Example configuration lives in `.env.example`.

Common options:

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

`AGENT_PLANNER_MODE=mock` uses the rule-based mock planner and does not call a real model.

`AGENT_PLANNER_MODE=llm` uses an OpenAI-compatible API to generate tool plans. It requires `LLM_API_KEY` or `OPENAI_API_KEY`.

The configuration entry point is:

```text
app/core/config.py
```

## Testing

Run all tests:

```bash
pytest
```

Or:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

The test suite covers:

- Tool unit tests.
- Agent Loop tests.
- API tests.
- Prompt construction tests.
- Configuration loading tests.
- Streaming error event tests.

## Docker

Build the image:

```bash
docker build -t mini-tool-agent .
```

Run the container:

```bash
docker run --env-file .env -p 8000:8000 mini-tool-agent
```

Use Docker Compose:

```bash
docker compose up --build
```

## Logging

The project uses structured logs to trace Agent request flows.

A successful tool call usually emits:

```text
request_started
agent_plan_created
tool_call_started
tool_call_finished
request_finished
```

On failure, it emits:

```text
tool_call_failed
request_finished
```

Important fields include:

- `trace_id`
- `message_preview`
- `planned_tools`
- `tool_name`
- `tool_arguments`
- `latency_ms`
- `error_code`
- `final_status`

## Known Limitations

- The current planner is still a rule-based mock planner, not a real LLM planner.
- `web_summary_mock` does not access the real network.
- `todo` uses in-memory storage, so data is lost after restart.
- Authentication and authorization are not implemented.
- Docker files are designed for local learning, not production deployment.
- Tool argument logging can be improved with stronger redaction.

## Roadmap

- Integrate a real LLM planner while keeping the mock planner for tests.
- Add timeout control for tool execution.
- Replace `TodoStore` with SQLite or another persistent storage.
- Add CORS configuration.
- Add CI.
- Improve Dockerfile with non-root user and healthcheck.
- Improve structured logging redaction.

## License

[MIT](LICENSE) @ 2026 lWaterLite
