# 子模块 5：FastAPI 服务化概念教学

## 1. 本子模块的学习目标

在前几个子模块中，我们已经逐步完成了：

- 使用 LLM API 进行对话。
- 使用 Pydantic 约束模型输出结构。
- 设计工具层，并让模型通过工具完成任务。
- 手写一个最小 Agent Loop，让模型可以“思考、调用工具、观察结果、继续回答”。

子模块 5 的目标是把这些能力从“命令行脚本”升级为“可被前端或其他服务调用的后端 API”。

也就是说，我们不再只是运行一个 Python 文件，然后在终端里看到结果，而是要让 Agent 变成一个服务：

- 前端页面可以调用它。
- 其他后端服务可以调用它。
- 测试代码可以稳定验证它。
- 未来可以部署到服务器上。

这个阶段的重点不是让 Agent 变得更聪明，而是让 Agent 变得更像一个真实工程。

## 2. 什么是服务化

服务化是指把一段本来只能在本地直接运行的程序，包装成一个可以通过网络访问的服务。

例如，原来我们可能这样调用 Agent：

```bash
python demo.py
```

服务化以后，调用方式可能变成：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"帮我计算 3 * (4 + 5)\"}"
```

这两种方式背后的 Agent 能力可以是同一套，但入口不同：

- 命令行入口适合学习、调试、演示。
- API 入口适合前端、自动化系统、第三方服务调用。

服务化的核心价值是把 Agent 从“一个脚本”变成“一个可集成的能力”。

## 3. 什么是 FastAPI

FastAPI 是一个 Python Web 框架，用来快速构建 HTTP API 服务。

它的特点包括：

- 使用 Python 类型注解描述请求和响应。
- 深度集成 Pydantic，适合做结构化数据校验。
- 自动生成接口文档。
- 支持同步和异步接口。
- 适合构建轻量、清晰、工程化的后端服务。

对于我们的 Agent 项目来说，FastAPI 主要承担“服务入口”的职责。

它不应该负责 Agent 的核心推理逻辑，也不应该直接写大量工具调用细节。更理想的结构是：

- FastAPI 负责接收请求、校验参数、返回响应。
- Agent Loop 负责执行对话流程。
- Tools 负责具体工具能力。
- Core 负责配置、日志、错误等基础设施。

## 4. 什么是 API

API 是 Application Programming Interface 的缩写，可以理解为“程序之间约定好的调用方式”。

在本子模块中，我们主要关注 HTTP API。

一个 HTTP API 通常包含：

- 请求方法，例如 `GET`、`POST`。
- 路径，例如 `/health`、`/chat`。
- 请求参数，例如 JSON body 或 query 参数。
- 响应数据，例如 JSON。
- 状态码，例如 `200`、`400`、`500`。

例如：

```http
POST /chat
Content-Type: application/json

{
  "message": "帮我计算 2 + 3"
}
```

服务返回：

```json
{
  "answer": "2 + 3 = 5",
  "used_tools": ["calculator"],
  "trace_id": "trace_abc123"
}
```

这里的 `/chat` 就是一个 API 接口。

## 5. HTTP 方法：GET 与 POST

HTTP 方法表示这次请求想做什么。

本阶段重点使用两个方法。

### 5.1 GET

`GET` 通常用于读取信息。

例如：

- `GET /health`：查看服务是否正常。
- `GET /tools`：查看当前 Agent 有哪些工具。

一般来说，`GET` 不应该改变服务内部状态。

### 5.2 POST

`POST` 通常用于提交数据，让服务处理。

例如：

- `POST /chat`：提交用户消息，让 Agent 生成回答。
- `POST /chat/stream`：提交用户消息，并以流式方式返回中间结果。

`POST` 常用于会创建、修改或触发计算的操作。

## 6. JSON 请求与响应

JSON 是前后端通信中非常常见的数据格式。

例如请求：

```json
{
  "message": "帮我总结今天的待办事项"
}
```

例如响应：

```json
{
  "answer": "你今天有 3 个待办事项。",
  "used_tools": ["todo"],
  "trace_id": "trace_001"
}
```

JSON 的优点是：

- 结构清晰。
- 前端和后端都容易处理。
- 适合表达嵌套数据。
- 可以自然映射到 Pydantic model。

## 7. 状态码

状态码是 HTTP 响应的一部分，用来表示请求处理结果。

常见状态码包括：

- `200 OK`：请求成功。
- `400 Bad Request`：请求参数有问题。
- `404 Not Found`：路径不存在或资源不存在。
- `422 Unprocessable Entity`：请求格式能解析，但字段校验不通过。FastAPI 默认常见。
- `500 Internal Server Error`：服务内部错误。

在 Agent 服务中，状态码可以帮助调用方判断问题发生在哪里。

例如：

- 用户传了空消息，可以返回 `400`。
- 请求 JSON 字段类型不对，可以由 FastAPI/Pydantic 返回 `422`。
- 工具执行时发生未知异常，可以返回 `500`，但不应该把完整异常栈直接暴露给用户。

## 8. Pydantic 在 API 中的作用

前面子模块已经学习过 Pydantic。在 FastAPI 中，Pydantic 的作用会更加明显。

它主要负责：

- 定义请求结构。
- 定义响应结构。
- 自动校验字段类型。
- 自动生成接口文档。
- 让 API 输入输出更稳定。

例如：

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户输入的消息")


class ChatResponse(BaseModel):
    answer: str
    used_tools: list[str]
    trace_id: str
```

有了这些模型后，`POST /chat` 的输入和输出就不再是随意的字典，而是有明确约束的工程接口。

这对后续维护非常重要。

## 9. 本阶段必须提供的接口

根据学习路线，子模块 5 至少需要提供 3 个接口，另有 1 个可选接口。

### 9.1 GET /health

作用：返回服务状态。

它通常用于：

- 本地确认服务是否启动。
- 部署后做健康检查。
- 让监控系统判断服务是否可用。

示例响应：

```json
{
  "status": "ok",
  "service": "mini-tool-agent"
}
```

这个接口不应该依赖 LLM，也不应该执行复杂逻辑。它越简单，越适合作为健康检查。

### 9.2 GET /tools

作用：返回当前 Agent 支持的工具列表。

它通常包含：

- 工具名称。
- 工具描述。
- 工具参数 schema。

示例响应：

```json
{
  "tools": [
    {
      "name": "calculator",
      "description": "执行安全的数学表达式计算",
      "parameters": {
        "expression": {
          "type": "string",
          "description": "要计算的数学表达式"
        }
      }
    }
  ]
}
```

这个接口的价值是让调用方知道 Agent 当前有哪些能力。

例如前端可以用它动态展示工具列表，测试也可以用它验证工具注册是否正确。

### 9.3 POST /chat

作用：接收用户消息，运行 Agent Loop，返回最终回答。

典型请求：

```json
{
  "message": "帮我计算 3 * (4 + 5)"
}
```

典型响应：

```json
{
  "answer": "计算结果是 27。",
  "used_tools": ["calculator"],
  "trace_id": "trace_abc123"
}
```

这个接口是本阶段最核心的接口。

它需要连接：

- API 请求模型。
- Agent Loop。
- 工具注册表。
- 错误处理。
- trace id。
- 响应模型。

### 9.4 POST /chat/stream

这是可选接口，用于练习 streaming。

普通 `/chat` 是一次性返回最终结果。

`/chat/stream` 则可以边执行边返回内容，例如：

- 先返回“收到问题”。
- 再返回“准备调用工具”。
- 再返回“工具返回结果”。
- 最后返回“最终回答”。

常见实现方式是 SSE，也就是 Server-Sent Events。

本阶段不一定要完整实现它，但需要先理解它的意义：

- 用户体验更好，可以看到 Agent 正在工作。
- 适合长任务。
- 适合展示中间步骤。
- 工程上会比普通接口更复杂。

## 10. 推荐工程目录结构

学习路线建议的目录结构如下：

```text
mini-tool-agent/
  app/
    main.py
    api/
      routes.py
      schemas.py
    agent/
      loop.py
      prompts.py
      models.py
    tools/
      base.py
      calculator.py
      file_search.py
      web_summary_mock.py
      todo.py
    core/
      config.py
      logging.py
      errors.py
  tests/
    test_tools_calculator.py
    test_tools_file_search.py
    test_agent_loop.py
    test_api_chat.py
  .env.example
  README.md
  pyproject.toml
```

这个结构背后的核心思想是分层。

一个小项目刚开始可以写在一个脚本里，但一旦开始服务化，就应该把不同职责拆开。拆分的目的不是追求复杂，而是让每个文件的责任更清楚。

## 11. 各目录职责

### 11.1 app/main.py

`main.py` 是 FastAPI 应用的入口。

它通常负责：

- 创建 `FastAPI()` 实例。
- 注册路由。
- 注册全局异常处理器。
- 配置应用启动时需要的资源。

它不应该写大量业务逻辑。

可以把它理解为“服务装配入口”。

### 11.2 app/api/routes.py

`routes.py` 存放 API 路由函数。

例如：

- `health()`
- `list_tools()`
- `chat()`

它的职责是：

- 接收请求。
- 调用下层业务逻辑。
- 把结果转换为响应模型。

它不应该直接实现工具细节，也不应该把 Agent Loop 的所有步骤写在路由函数里。

### 11.3 app/api/schemas.py

`schemas.py` 存放 API 请求和响应模型。

例如：

- `ChatRequest`
- `ChatResponse`
- `ToolInfo`
- `ErrorResponse`

这样做的好处是：

- 路由代码更清爽。
- 请求响应结构集中管理。
- 测试和文档更容易维护。

### 11.4 app/agent/loop.py

`loop.py` 存放 Agent Loop 核心逻辑。

它应该负责：

- 接收用户消息。
- 构造 prompt。
- 调用模型或 mock 模型。
- 解析模型动作。
- 调用工具。
- 汇总观察结果。
- 生成最终回答。

API 层不应该关心这些细节。

### 11.5 app/agent/prompts.py

`prompts.py` 存放 prompt 模板。

例如：

- 系统提示词。
- 工具调用格式说明。
- 输出格式要求。

把 prompt 单独放出来的好处是：

- 方便调整模型行为。
- 避免 prompt 散落在各个业务函数中。
- 后续可以给 prompt 单独写测试。

### 11.6 app/agent/models.py

`models.py` 可以存放 Agent 内部使用的数据结构。

例如：

- `AgentResult`
- `ToolCallRecord`
- `AgentStep`

这些模型不一定等同于 API 响应模型。

API model 是对外契约，Agent model 是内部结构。两者可以相似，但最好不要完全混在一起。

### 11.7 app/tools/base.py

`base.py` 存放工具抽象。

例如：

- 工具协议。
- 工具基础类。
- 工具注册表。
- 工具参数 schema 的统一格式。

它的价值是让不同工具有一致的接口。

如果没有统一接口，Agent Loop 调用工具时就会越来越混乱。

### 11.8 app/tools/calculator.py

计算器工具。

它可以复用子模块 3 中的安全计算器思想。

注意：计算器不能直接使用不受限制的 `eval`。

更推荐使用 AST 白名单方式，只允许安全的数学表达式。

### 11.9 app/tools/file_search.py

文件搜索工具。

它可以用于在指定目录中查找文本或文件。

注意事项：

- 限制搜索根目录，避免读取系统敏感文件。
- 对用户输入做校验。
- 返回结果数量要有限制，避免响应过大。

### 11.10 app/tools/web_summary_mock.py

模拟网页总结工具。

在早期学习阶段，可以先使用 mock 工具，不直接访问真实网络。

这样做的好处是：

- 测试稳定。
- 不依赖网络环境。
- 聚焦 Agent 工程结构，而不是网页抓取细节。

### 11.11 app/tools/todo.py

待办事项工具。

可以练习：

- 添加待办。
- 查看待办。
- 标记完成。

注意：如果工具内部使用全局列表保存状态，需要理解它在服务化场景下的问题。

例如多个用户同时访问时，所有人可能共享同一份待办数据。这在学习阶段可以接受，但真实项目中需要数据库或用户隔离机制。

### 11.12 app/core/config.py

配置模块。

它通常负责读取：

- 服务名称。
- 环境变量。
- API key。
- 模型名称。
- 超时时间。
- 是否开启 debug。

配置不应该散落在代码各处。

例如，不建议在业务代码里直接写：

```python
api_key = "sk-..."
```

更好的方式是从环境变量读取。

### 11.13 app/core/logging.py

日志模块。

日志用于记录服务运行过程。

在 Agent 服务中，日志尤其重要，因为一次请求可能包括：

- 收到用户输入。
- 生成 trace id。
- 调用模型。
- 选择工具。
- 执行工具。
- 生成最终回答。

日志可以帮助我们排查问题。

但日志也要注意不要泄露敏感信息，例如 API key、用户隐私内容等。

### 11.14 app/core/errors.py

错误模块。

它可以存放：

- 自定义异常类型。
- 错误码。
- 统一错误响应构造函数。

统一错误处理的好处是：

- 调用方更容易理解错误。
- 测试更稳定。
- 不会在不同接口中返回完全不同的错误格式。

## 12. API 层与 Agent 层的边界

服务化后，一个非常重要的工程问题是：哪些逻辑应该放在 API 层，哪些逻辑应该放在 Agent 层？

推荐边界如下。

API 层负责：

- HTTP 路由。
- 请求校验。
- 响应模型。
- 状态码。
- 把异常转换成统一错误响应。

Agent 层负责：

- prompt 构造。
- 模型调用。
- 工具调用流程。
- 中间步骤记录。
- 最终结果生成。

Tools 层负责：

- 执行具体能力。
- 校验工具自身参数。
- 返回结构化工具结果。

Core 层负责：

- 配置。
- 日志。
- 错误定义。
- trace id 等基础能力。

这条边界很重要。否则项目稍微变大以后，路由函数会变成一个什么都做的巨大函数。

## 13. Trace ID

trace id 是一次请求的唯一标识。

例如：

```text
trace_20260525_abcd1234
```

它的作用是把一次请求中的所有日志、工具调用、错误信息串起来。

假设用户说：

“刚刚那个请求失败了。”

如果没有 trace id，我们很难知道是哪一次请求。

如果响应里有 trace id，日志里也有同一个 trace id，就可以快速定位。

在本阶段，`POST /chat` 的响应中应该包含 trace id：

```json
{
  "answer": "计算结果是 27。",
  "used_tools": ["calculator"],
  "trace_id": "trace_abc123"
}
```

## 14. Used Tools

`used_tools` 表示 Agent 在回答过程中实际使用过哪些工具。

它的作用包括：

- 方便调试。
- 提高结果可解释性。
- 让前端展示 Agent 的执行过程。
- 便于测试断言。

例如，用户问：

```text
帮我计算 12 * 8
```

响应中可以包含：

```json
{
  "answer": "12 * 8 = 96",
  "used_tools": ["calculator"],
  "trace_id": "trace_001"
}
```

如果用户只是打招呼：

```text
你好
```

响应中可能是：

```json
{
  "answer": "你好，我可以帮助你计算、搜索文件或管理待办事项。",
  "used_tools": [],
  "trace_id": "trace_002"
}
```

## 15. 统一错误返回格式

工程中不建议每个接口随意返回不同格式的错误。

例如，有的接口返回：

```json
{
  "error": "message is empty"
}
```

另一个接口返回：

```json
{
  "detail": "工具不存在"
}
```

还有一个接口返回：

```json
{
  "msg": "unknown error"
}
```

这样会让调用方很难处理。

更推荐统一格式，例如：

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "用户消息不能为空",
    "trace_id": "trace_abc123"
  }
}
```

常见错误码可以包括：

- `INVALID_REQUEST`：请求参数不合法。
- `TOOL_NOT_FOUND`：工具不存在。
- `TOOL_EXECUTION_ERROR`：工具执行失败。
- `AGENT_ERROR`：Agent Loop 执行失败。
- `INTERNAL_ERROR`：未知服务错误。

注意：真实项目中，不应该直接把 Python 异常栈返回给用户。异常栈应该记录到日志中，响应里只返回对用户有意义的信息。

## 16. 参数校验

参数校验是服务化后非常关键的一层防线。

需要校验的内容包括：

- 用户消息不能为空。
- 用户消息长度不能无限制。
- 工具参数类型必须正确。
- 文件路径不能越权。
- 数字范围不能过大。
- 返回内容不能无限大。

在 FastAPI 中，可以用 Pydantic 做第一层校验。

例如：

```python
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
```

工具内部也应该做自己的校验。

原因是工具将来不一定只被 API 调用，也可能被测试、脚本、其他 Agent 调用。

## 17. 同步与异步

FastAPI 支持同步函数和异步函数。

同步接口示例：

```python
@router.post("/chat")
def chat(request: ChatRequest) -> ChatResponse:
    ...
```

异步接口示例：

```python
@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    ...
```

什么时候用异步？

当接口中存在大量等待型操作时，异步可能更合适，例如：

- 调用远程 LLM API。
- 访问数据库。
- 调用外部 HTTP 服务。

但异步不是越多越好。

学习阶段可以先使用同步方式，把结构做清楚。后续接入真实 LLM API 时，再考虑是否改成异步。

## 18. 应用状态与依赖注入

服务运行期间，有些对象不适合每次请求都重新创建。

例如：

- 工具注册表。
- Agent 实例。
- 配置对象。
- HTTP 客户端。

这些对象可以在应用启动时创建，然后在请求中复用。

FastAPI 提供了依赖注入机制，可以通过 `Depends` 把这些对象传给路由函数。

简单理解，依赖注入就是：

“路由函数需要什么，由框架或统一函数提供，而不是在函数内部到处手动 new。”

这样做的好处是：

- 更容易测试。
- 更容易替换 mock。
- 更容易管理资源生命周期。

本阶段不需要把依赖注入用得很复杂，但要知道它是 FastAPI 工程中非常常见的组织方式。

## 19. Streaming 与 SSE

Streaming 是流式返回。

普通请求像这样：

```text
用户发送请求 -> 服务处理很久 -> 一次性返回结果
```

流式请求像这样：

```text
用户发送请求 -> 服务逐段返回中间内容 -> 最后返回结束信号
```

SSE 是 Server-Sent Events 的缩写，是一种常见的服务端向客户端持续推送文本事件的方式。

对于 Agent 来说，streaming 很适合返回：

- 当前正在思考。
- 准备调用哪个工具。
- 工具返回了什么。
- 最终答案是什么。

不过 streaming 会引入更多工程问题：

- 如何定义事件格式。
- 如何处理过程中出错。
- 如何让前端识别结束。
- 如何测试流式响应。

所以学习路线把 `/chat/stream` 标为可选是合理的。先做好普通 `/chat`，再做 streaming。

## 20. 测试的重要性

服务化以后，测试会变得更重要。

因为我们不仅要测试单个函数，还要测试接口行为。

学习路线要求 `/chat` 至少有 3 个测试用例。

建议至少覆盖：

1. 普通问答：用户打招呼，不调用工具也能返回回答。
2. 工具调用：用户提出计算问题，返回结果并记录 `used_tools`。
3. 错误输入：用户消息为空或格式错误时，返回明确错误。

还可以增加：

- 工具不存在时的错误。
- 工具执行失败时的错误。
- trace id 是否存在。
- 响应字段是否符合 schema。

## 21. FastAPI TestClient

FastAPI 提供 `TestClient`，可以在测试中直接调用 API，而不需要真的启动一个服务器。

示例：

```python
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

这类测试的价值很高，因为它验证的是完整 API 行为，而不是单个函数的局部行为。

## 22. README 与 curl 示例

一个工程即使代码写得不错，如果没有运行说明，也会很难交接。

本阶段 README 至少应该包含：

- 如何安装依赖。
- 如何启动服务。
- 如何调用 `/health`。
- 如何调用 `/tools`。
- 如何调用 `/chat`。
- 测试如何运行。

例如：

```bash
uvicorn app.main:app --reload
```

调用接口：

```bash
curl http://127.0.0.1:8000/health
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"帮我计算 3 * (4 + 5)\"}"
```

README 不只是给别人看的，也是给未来的自己看的。

## 23. .env.example

`.env.example` 是环境变量示例文件。

它通常不存放真实密钥，只存放变量名称和示例值。

例如：

```text
APP_NAME=mini-tool-agent
APP_ENV=development
OPENAI_API_KEY=your_api_key_here
MODEL_NAME=gpt-4.1-mini
REQUEST_TIMEOUT_SECONDS=30
```

注意：

- `.env.example` 可以提交到代码仓库。
- `.env` 通常不应该提交，因为里面可能有真实密钥。
- API key 不应该硬编码在 Python 文件中。

## 24. 工程注意事项

### 24.1 不要把所有逻辑写在路由里

路由函数应该薄一点。

它可以做请求接收、调用服务、返回响应，但不应该把 prompt、工具调用、错误处理、日志细节全部堆进去。

### 24.2 对外模型和内部模型可以分开

API 响应模型是对外承诺。

Agent 内部模型是内部实现。

如果两者完全混用，以后内部结构一变，API 可能也被迫变化。

### 24.3 错误要可预期

调用方希望知道：

- 是我传错参数了吗？
- 是工具失败了吗？
- 是 Agent 内部失败了吗？
- 我应该重试吗？

统一错误格式可以帮助调用方做判断。

### 24.4 不要泄露敏感信息

响应和日志都要注意敏感信息。

不应该暴露：

- API key。
- 完整异常栈。
- 系统文件路径。
- 用户隐私内容。

### 24.5 注意全局状态

服务化后，程序不是运行一次就退出，而是长期运行。

如果你在全局变量里保存待办事项、聊天历史或工具状态，就要思考：

- 多个用户会不会共享同一份数据？
- 测试之间会不会互相影响？
- 服务重启后数据是否会丢失？

学习阶段可以使用内存状态，但要清楚它的限制。

### 24.6 注意超时

Agent 可能调用模型或工具。

如果某个步骤一直不返回，整个请求就会卡住。

真实项目中通常要设置：

- LLM 调用超时。
- 工具执行超时。
- 总请求超时。

本阶段可以先了解概念，后续逐步实现。

### 24.7 注意日志粒度

日志太少，排查问题困难。

日志太多，又会干扰阅读，甚至暴露隐私。

比较合适的日志包括：

- 请求开始和结束。
- trace id。
- 使用了哪些工具。
- 工具是否成功。
- 错误码。

不建议无脑打印完整 prompt、完整用户输入或完整模型响应，尤其是在真实项目中。

### 24.8 注意测试可控性

如果测试直接调用真实 LLM API，会带来很多问题：

- 慢。
- 贵。
- 不稳定。
- 网络环境可能失败。
- 模型输出有随机性。

所以本阶段更推荐使用 mock LLM。

先把工程结构、接口行为和 Agent Loop 测稳定，再接真实模型。

## 25. 一个请求的完整流转过程

以 `POST /chat` 为例，一次请求大致可以这样流转：

```text
用户发送 JSON 请求
  -> FastAPI 接收请求
  -> Pydantic 校验 ChatRequest
  -> 生成 trace id
  -> 调用 Agent Loop
  -> Agent 判断是否需要工具
  -> 调用工具并获得观察结果
  -> Agent 生成最终回答
  -> API 层组装 ChatResponse
  -> 返回 JSON 响应
```

这条链路中的每一层都应该有清楚职责。

如果出现错误，也应该能知道错误来自哪一层：

- 请求字段错误：API/Pydantic 层。
- 工具参数错误：Tools 层。
- 模型输出格式错误：Agent 层。
- 未知异常：Core 错误处理层。

## 26. 本阶段应该建立的工程意识

子模块 5 的核心不只是 FastAPI 语法，而是工程意识。

你需要开始思考：

- 一个 Agent 项目如何组织目录？
- 哪些代码是 API 层，哪些代码是 Agent 层？
- 什么是对外接口契约？
- 请求和响应为什么要有 model？
- 错误为什么要统一格式？
- trace id 为什么重要？
- 工具列表为什么要可查询？
- 为什么测试不应该依赖真实 LLM？
- README 为什么也是工程的一部分？

这些意识会直接影响后续项目能不能继续扩展。

## 27. 学习后的自检问题

完成本子模块概念学习后，可以尝试回答下面的问题：

1. 服务化和命令行脚本的主要区别是什么？
2. FastAPI 在 Agent 项目中主要负责哪一层？
3. 为什么 `/health` 接口不应该依赖 LLM？
4. `/tools` 接口为什么要返回参数 schema？
5. `POST /chat` 的请求模型和响应模型分别应该包含什么？
6. 为什么 API 错误返回格式要统一？
7. trace id 的作用是什么？
8. `used_tools` 对调试和用户体验有什么帮助？
9. API 层和 Agent Loop 层的边界应该如何划分？
10. 为什么测试中更推荐使用 mock LLM，而不是直接调用真实模型？
11. `.env.example` 和 `.env` 有什么区别？
12. 全局变量在服务化场景中可能带来什么问题？
13. streaming 和普通接口的区别是什么？
14. 为什么 README 也是工程交付的一部分？

## 28. 下一步实践方向

接下来做练习时，可以按照下面顺序推进：

1. 搭建 `app/` 目录结构。
2. 实现 `GET /health`。
3. 定义 API 请求和响应 Pydantic model。
4. 实现工具基础结构和工具注册表。
5. 接入计算器、文件搜索、mock 网页总结、待办工具。
6. 把已有 Agent Loop 移入 `app/agent/loop.py`。
7. 实现 `GET /tools`。
8. 实现 `POST /chat`。
9. 增加统一错误处理。
10. 编写至少 3 个 `/chat` 测试用例。
11. 编写 README 和 curl 示例。
12. 有余力时再实现 `/chat/stream`。

这个顺序可以避免一开始就陷入完整工程的复杂度。先让服务跑起来，再逐步补齐工程能力。

