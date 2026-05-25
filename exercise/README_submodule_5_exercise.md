# 子模块 5 练习：FastAPI 服务化 Mini Tool Agent

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API_service-green)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-orange)
![pytest](https://img.shields.io/badge/tests-pytest-informational)

这份文档只说明子模块 5 的练习工程。根目录的 `README.md` 面向整个 `mini-tool-agent` 项目；本文件面向你学习“如何把最小 Agent 服务化”为一个可运行、可测试、可扩展的小型后端工程。

## 1. 练习目标

完成本练习后，你应该能够理解：

- 如何用 FastAPI 把 Agent 包装成 HTTP API。
- 如何用 Pydantic 定义请求和响应模型。
- 如何组织一个小型后端工程的目录结构。
- 如何区分 API 层、Agent 层、Tools 层和 Core 层。
- 如何用依赖注入管理应用状态。
- 如何处理同步接口、异步接口和 streaming 接口。
- 如何设计统一错误返回格式。
- 如何为工具层、Agent 层和 API 层编写测试。

本练习不是单文件脚本，而是一个系统性工程项目。你应该重点阅读代码之间的边界，而不只是某一个函数的实现。

## 2. 当前工程结构

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
      calculator.py
      file_search.py
      web_summary_mock.py
      todo.py
  tests/
    fixtures/
    test_agent_loop.py
    test_agent_prompts.py
    test_api_chat.py
    test_tools_calculator.py
    test_tools_file_search.py
  exercise/
    README_submodule_5_exercise.md
  .env.example
  pyproject.toml
```

## 3. 代码分层说明

- `app/main.py`：FastAPI 应用入口，负责创建应用、注册路由、注册异常处理器。
- `app/api/schemas.py`：API 请求和响应模型，例如 `ChatRequest`、`ChatResponse`。
- `app/api/routes.py`：HTTP 路由定义，例如 `/health`、`/tools`、`/chat`、`/chat/stream`。
- `app/api/dependencies.py`：应用状态和依赖注入，例如工具注册表、Agent 实例、Todo 存储。
- `app/agent/loop.py`：Agent 核心流程，负责规划工具步骤、执行工具、汇总最终回答。
- `app/agent/prompts.py`：工具 prompt 构造逻辑，后续接真实 LLM 时会更重要。
- `app/tools/base.py`：工具基类和统一工具结果模型。
- `app/tools/registry.py`：工具注册表，Agent 通过它按名称查找工具。
- `app/tools/calculator.py`：安全计算器工具，使用 AST 白名单计算表达式。
- `app/tools/file_search.py`：文件搜索工具，在限定目录下搜索文本。
- `app/tools/web_summary_mock.py`：模拟网页摘要工具，不访问真实网络。
- `app/tools/todo.py`：内存待办工具，按 `session_id` 隔离数据。
- `app/core/config.py`：配置读取。
- `app/core/errors.py`：统一异常类型和错误响应。
- `app/core/logging.py`：日志配置。
- `app/core/trace.py`：trace id 生成。

## 4. 安装依赖

在 `mini-tool-agent` 根目录下执行：

```bash
uv sync
```

如果你不使用 `uv`，也可以执行：

```bash
pip install -e .
```

推荐优先使用项目已有的虚拟环境：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 5. 环境变量

复制示例配置：

```powershell
copy .env.example .env
```

当前子模块 5 使用规则型 mock planner，不会调用真实 LLM，所以即使没有真实 API key，也可以运行服务和测试。

需要重点关注的配置：

- `APP_NAME`：服务名称。
- `APP_ENV`：运行环境。
- `FILE_SEARCH_ROOT`：文件搜索工具允许搜索的根目录。
- `MAX_FILE_SEARCH_RESULTS`：文件搜索最多返回多少条。
- `MAX_AGENT_STEPS`：默认最多允许 Agent 执行多少个工具步骤。

## 6. 启动服务

在 `mini-tool-agent` 根目录下执行：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

或：

```bash
uvicorn app.main:app --reload
```

服务默认地址：

```text
http://127.0.0.1:8000
```

接口文档地址：

```text
http://127.0.0.1:8000/docs
```

## 7. API 使用示例

### 7.1 健康检查

```powershell
curl http://127.0.0.1:8000/health
```

预期返回：

```json
{
  "status": "ok",
  "service": "mini-tool-agent",
  "environment": "development"
}
```

### 7.2 查看工具列表

```powershell
curl http://127.0.0.1:8000/tools
```

这个接口会返回工具名称、说明和参数 schema。前端或其他服务可以通过它了解 Agent 当前有哪些能力。

### 7.3 普通对话

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"你好\"}"
```

### 7.4 调用计算器工具

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"计算 3 * (4 + 5)\"}"
```

### 7.5 使用 max_steps 限制工具步数

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"计算 1 + 2 并查看待办\",\"max_steps\":1}"
```

这类请求会触发步数限制。因为它可能需要多个工具步骤，而 `max_steps` 只允许 1 步。

### 7.6 使用 session_id 隔离待办

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"添加待办 写子模块5总结\",\"session_id\":\"student_a\"}"
```

查看同一个 session 的待办：

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"查看待办\",\"session_id\":\"student_a\"}"
```

换成另一个 `session_id` 时，会看到另一份独立的待办列表。

### 7.7 Streaming 接口

```powershell
curl -N -X POST http://127.0.0.1:8000/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"计算 1 + 2\"}"
```

`/chat/stream` 会以 SSE 格式返回多个事件，例如：

- `start`
- `tool_call`
- `tool_result`
- `final`

这可以帮助你观察 Agent 的中间执行过程。

## 8. 运行测试

运行全部测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

运行 API 测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_chat.py
```

运行工具测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_tools_calculator.py tests/test_tools_file_search.py
```

当前测试覆盖：

- 安全计算器。
- 文件搜索。
- Agent Loop。
- Prompt 构造。
- `/health`、`/tools`、`/chat`、`/chat/stream`。
- `max_steps`。
- `session_id` 隔离。

## 9. 阅读代码建议

建议按下面顺序阅读：

1. `app/main.py`：先看应用如何被创建。
2. `app/api/routes.py`：理解 HTTP 请求如何进入系统。
3. `app/api/schemas.py`：理解 API 输入输出契约。
4. `app/api/dependencies.py`：理解应用状态和工具注册。
5. `app/tools/base.py` 与 `app/tools/registry.py`：理解工具抽象。
6. `app/tools/calculator.py`：复习安全工具实现。
7. `app/tools/todo.py`：理解有状态工具和 session 隔离。
8. `app/agent/loop.py`：理解 Agent 如何规划和执行工具。
9. `app/core/errors.py`：理解统一错误格式。
10. `tests/`：对照测试理解工程行为。

## 10. 需要注意的点

- 当前 Agent 不是由真实 LLM 驱动，而是规则型 mock planner。
- `web_summary_mock` 不访问真实网络，目的是让测试稳定。
- `todo` 使用内存存储，服务重启后数据会丢失。
- `session_id` 只用于隔离内存待办，不是认证系统。
- `file_search` 只应该在受控目录中搜索，不要放开到任意系统路径。
- `calculator` 使用 AST 白名单，不要改成直接 `eval`。
- `max_steps` 是防止 Agent 无限执行工具的基础保护。
- API 错误响应不应该暴露完整异常栈，异常栈应进入日志。
- streaming 接口比普通接口更复杂，后续要特别注意错误事件和客户端断连。

## 11. 已实现能力

- FastAPI 应用工厂。
- Pydantic 请求和响应模型。
- `/health`、`/tools`、`/chat`、`/chat/stream`。
- 工具注册表。
- 工具工厂列表。
- 安全计算器。
- 文件搜索。
- mock 网页摘要。
- session 隔离的内存待办。
- 多工具顺序执行。
- 请求级 `max_steps`。
- trace id。
- 统一错误响应。
- 基础日志。
- 单元测试和 API 测试。

## 12. 练习任务

### 练习 1：为 streaming 增加错误事件

当前 `/chat/stream` 主要展示成功路径。

请尝试让 streaming 在工具执行失败时返回：

```text
event: error
data: {"code": "...", "message": "...", "trace_id": "..."}
```

思考：

- 错误事件之后是否应该继续发送 `final`？
- API 普通错误响应和 SSE 错误事件应该如何统一？

### 练习 2：为工具执行增加超时

给工具调用增加超时保护。

建议方向：

- 在 `Settings` 中增加 `tool_timeout_seconds`。
- 在 `AgentService` 中用 `asyncio.wait_for` 包裹工具调用。
- 超时时返回 `TOOL_EXECUTION_ERROR`。

思考：

- 超时应该是全局配置，还是每个工具可以单独配置？

### 练习 3：增强文件搜索工具

当前文件搜索只返回每个文件的第一条匹配。

请尝试支持：

- 每个文件返回多条匹配。
- 返回匹配行的上下文。
- 排除 `__pycache__`、`.venv` 等目录。

思考：

- API 响应应该返回原始匹配数据，还是只返回摘要文本？

### 练习 4：接入真实 LLM Planner

当前 planner 是规则型实现。

请尝试新增一个 LLM planner：

- 输入用户消息。
- 输入工具 schema。
- 输出结构化工具计划。
- 用 Pydantic 校验模型输出。

思考：

- 测试中如何避免直接调用真实 LLM？
- mock planner 和真实 planner 应该如何切换？

### 练习 5：增加工具调用审计日志

为每次工具调用记录结构化日志。

建议记录：

- `trace_id`
- `tool_name`
- `success`
- `duration_ms`
- `error_code`

思考：

- 用户输入、工具参数和工具结果是否都适合直接写入日志？

### 练习 6：将 TodoStore 替换为 SQLite

当前 `TodoStore` 是内存存储。

请尝试实现 SQLite 版本：

- 按 `session_id` 查询。
- 支持新增、查看、完成待办。
- 测试中使用临时数据库。

思考：

- 数据库连接应该放在应用状态里，还是工具内部？

### 练习 7：增加 CORS 配置

如果未来要让浏览器前端调用 API，需要配置 CORS。

建议方向：

- 在 `Settings` 中增加允许的 origins。
- 在 `main.py` 中注册 `CORSMiddleware`。

思考：

- 学习项目可以允许所有来源，真实项目为什么不应该这样做？

## 13. 自检问题

完成阅读和练习后，尝试回答：

1. API 层为什么不应该直接写工具执行细节？
2. `AppState` 解决了什么问题？
3. `Depends(get_app_state)` 属于什么机制？
4. 为什么 `/health` 可以是同步函数，而 `/chat` 更适合异步函数？
5. `ToolRegistry` 的价值是什么？
6. `max_steps` 防止了哪类风险？
7. `session_id` 隔离解决了什么问题，又没有解决什么问题？
8. SSE streaming 和普通 JSON 响应有什么区别？
9. 为什么测试里不直接调用真实 LLM？
10. 如果要部署这个服务，你还需要补哪些工程能力？

