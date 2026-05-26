# 子模块 6：测试、Mock 与覆盖率概念教学

## 1. 本子模块的学习目标

前面的子模块已经把 `mini-tool-agent` 从一个最小脚本逐步推进成了一个 FastAPI 服务化工程。

子模块 6 的核心目标是：

- 把项目从“能跑”变成“稳定可改”。
- 学会用测试保护 Agent 行为的关键边界。
- 学会使用 Mock，让测试不依赖真实 LLM API。
- 学会阅读覆盖率报告，判断哪些模块还缺少测试保护。

一句话概括：

测试不是为了证明代码永远没错，而是为了让你改代码时更快发现哪里被改坏了。

## 2. 为什么 Agent 项目特别需要测试

Agent 项目比普通后端接口更容易出现“不稳定行为”。

原因包括：

- LLM 输出天然可能变化。
- 工具调用链路比普通函数调用更长。
- 模型输出可能格式不稳定。
- 工具参数可能来自模型，而不是直接来自用户。
- 一次请求可能包含多轮推理和多次工具调用。
- Agent loop 如果控制不好，可能无限循环或超过最大步数。
- 错误可能发生在 API 层、Agent 层、工具层、模型层或解析层。

所以测试的重点不是只验证“正常路径能跑通”，而是要保护关键边界。

例如：

- 工具收到非法参数时是否能安全失败？
- 模型输出不合法 JSON 时是否能被识别？
- 工具失败后 Agent 是否能给出明确错误？
- `/chat` 是否永远返回符合 schema 的结构？
- 不调用真实模型时，测试是否也能稳定运行？

## 3. 什么是测试

测试是用代码验证代码行为。

例如：

```python
def test_calculator_addition():
    result = safe_eval("1 + 2", trace_id="trace_test")

    assert result == 3
```

这个测试表达了一个明确预期：

当输入是 `"1 + 2"` 时，计算结果应该是 `3`。

如果以后你改了计算器代码，导致这个测试失败，就说明某个行为被破坏了。

## 4. 测试的价值

测试主要有四个作用。

### 4.1 防止回归

回归是指原来正确的功能，因为后续修改又坏掉了。

例如你给计算器增加幂运算后，不小心把除法改坏了。测试可以立刻发现。

### 4.2 说明行为

好的测试也是一种文档。

例如看到下面的测试，你就能知道系统应该拒绝空消息：

```python
def test_chat_validation_error():
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422
```

### 4.3 支持重构

重构是指在不改变外部行为的前提下改善内部结构。

如果有测试保护，你就能更大胆地拆函数、拆模块、优化结构。

### 4.4 提高定位效率

测试失败时，如果失败信息清楚，就能快速判断问题发生在哪里。

例如：

- 工具单元测试失败：大概率是某个工具内部逻辑坏了。
- API 测试失败：可能是路由、schema 或异常处理坏了。
- Agent loop 测试失败：可能是规划、工具执行顺序或最终回答汇总坏了。

## 5. 什么是单元测试

单元测试是测试一个较小、较独立的代码单元。

在本项目中，单元可以是：

- 一个工具函数。
- 一个工具类。
- 一个解析函数。
- 一个 prompt 构造函数。
- 一个配置读取函数。

例如测试计算器工具：

```python
def test_safe_eval_basic_expression():
    assert safe_eval("3 * (4 + 5)", "trace_test") == 27
```

单元测试的特点：

- 范围小。
- 执行快。
- 错误定位清晰。
- 尽量不依赖网络、数据库、真实 LLM。

## 6. 什么是集成测试

集成测试是验证多个模块组合起来是否能正常工作。

例如 API 测试：

```python
def test_chat_with_calculator():
    response = client.post("/chat", json={"message": "计算 3 * (4 + 5)"})

    assert response.status_code == 200
    assert response.json()["used_tools"] == ["calculator"]
```

这个测试同时经过了：

- FastAPI 路由。
- Pydantic 请求模型。
- Agent loop。
- 工具注册表。
- calculator 工具。
- Pydantic 响应模型。

它不是单独测某个函数，而是在测一条完整链路。

集成测试的特点：

- 更接近真实使用方式。
- 更容易发现模块之间的连接问题。
- 失败后定位可能比单元测试更复杂。

## 7. 什么是端到端测试

端到端测试通常是从用户视角测试整个系统。

例如：

- 启动真实服务。
- 通过 HTTP 请求访问 `/chat`。
- 观察真实响应。

本阶段主要使用 FastAPI `TestClient`，它不需要真正启动一个服务进程，也能测试 API 行为。

严格来说，这更接近 API 集成测试，而不是真正的端到端测试。

真正端到端测试可能还包括：

- 浏览器前端。
- 真实后端服务。
- 真实数据库。
- 真实部署环境。

这部分可以后续再做。

## 8. 什么是 Mock

Mock 是一种测试替身。

它的作用是用一个可控对象替代真实依赖。

例如真实 LLM API 有几个问题：

- 会花钱。
- 会变慢。
- 需要网络。
- 输出可能不稳定。
- API key 可能缺失。

所以测试中不适合直接调用真实 LLM。

更好的方式是用 mock 模型：

```python
class FakeLLM:
    def complete(self, messages):
        return '{"action": "calculator", "arguments": {"expression": "1 + 2"}}'
```

这样测试可以稳定验证 Agent loop 的行为。

## 9. Mock、Stub、Fake 的区别

这些概念经常混用，学习阶段可以先理解大概区别。

### 9.1 Stub

Stub 是最简单的替身，通常只返回固定结果。

例如：

```python
class StubModel:
    def complete(self, messages):
        return "固定回答"
```

### 9.2 Fake

Fake 是一个简化版实现。

它比 stub 更像真实对象，但通常只适合测试。

例如内存版 `TodoStore` 可以看作数据库的 fake。

### 9.3 Mock

Mock 不只是返回结果，还可以验证它是否被正确调用。

例如验证某个工具是否被调用了一次，调用参数是否正确。

在 Python 中，可以使用 `unittest.mock` 提供的 `Mock`、`AsyncMock`、`patch`。

## 10. 为什么测试不要依赖真实模型

Agent 测试最重要的一条原则是：

大多数测试不应该调用真实模型。

原因包括：

- 成本不可控。
- 网络不稳定。
- 输出不稳定。
- 运行速度慢。
- CI 环境可能没有 API key。
- 测试失败时，很难判断是代码问题还是模型变化。

正确做法是：

- 单元测试中使用 mock 模型。
- Agent loop 测试中固定模型输出。
- 少量手动测试或单独标记的集成测试可以调用真实模型。
- 调用真实模型的测试默认不在普通测试命令中运行。

## 11. 测试分层

学习路线中提到四类测试：

1. 工具单元测试。
2. 输出解析测试。
3. Agent loop 测试。
4. API 测试。

这四层从底到上，逐步覆盖整个系统。

可以理解为：

```text
工具单元测试
  -> 输出解析测试
  -> Agent loop 测试
  -> API 测试
```

越底层的测试越快、越精准。

越上层的测试越接近真实使用场景，但失败后定位成本更高。

## 12. 工具单元测试

工具单元测试关注每个工具自身是否正确。

例如：

- `calculator` 能否计算正常表达式。
- `calculator` 是否拒绝函数调用。
- `file_search` 是否能找到关键词。
- `todo` 是否能添加、查看、完成待办。
- `web_summary_mock` 是否返回稳定结构。

工具测试至少应该覆盖三类情况。

### 12.1 正常输入

例如：

```python
def test_calculator_normal_expression():
    assert safe_eval("2 + 3", "trace_test") == 5
```

### 12.2 非法输入

例如：

```python
def test_calculator_rejects_function_call():
    with pytest.raises(AppError):
        safe_eval("__import__('os')", "trace_test")
```

### 12.3 工具内部异常

例如：

- 除数为 0。
- 文件搜索目录不存在。
- 待办 ID 不存在。
- 参数类型错误。

工具层测试的重点是：工具不能因为坏输入而失控。

## 13. 输出解析测试

输出解析测试关注模型输出能否被正确解析。

真实 LLM 输出可能出现这些情况：

- 合法 JSON。
- JSON 字段缺失。
- 字段类型错误。
- 输出前后有多余文本。
- 输出包含 Markdown 代码块。
- 输出完全不是 JSON。

例如模型输出：

```text
好的，我会调用工具：

```json
{"action": "calculator", "arguments": {"expression": "1 + 2"}}
```

```
解析器需要决定：

- 是否允许提取代码块中的 JSON？
- 是否要求输出只能是纯 JSON？
- 字段缺失时返回什么错误？
- 多余字段是否允许？
```
在 Agent 项目中，解析器是高风险边界，因为模型输出并不总是完全听话。

## 14. Agent Loop 测试

Agent loop 测试关注 Agent 的流程是否正确。

它不应该直接测试真实模型能力，而应该用 mock 模型或规则型 planner 构造稳定场景。

常见测试包括：

- 不需要工具时直接回答。
- 一次工具调用。
- 多次工具调用。
- 超过最大轮数或 `max_steps`。
- 工具失败后的错误处理。
- 工具结果是否被正确汇总到最终回答。
- `used_tools` 是否正确记录。
- `trace_id` 是否贯穿整个流程。

例如：

```python
@pytest.mark.asyncio
async def test_agent_uses_calculator():
    result = await agent.run("计算 2 + 3", trace_id="trace_test")

    assert result.used_tools == ["calculator"]
```

## 15. API 测试

API 测试关注 HTTP 层行为。

FastAPI 提供 `TestClient`，可以不用启动真实服务就测试接口。

例如：

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

API 测试应该覆盖：

- `GET /health`
- `GET /tools`
- `POST /chat`
- 请求参数错误。
- 工具调用成功。
- 工具调用失败。
- streaming 成功路径。

## 16. Streaming 测试

`/chat/stream` 和普通 `/chat` 不同。

普通接口一次性返回 JSON。

Streaming 接口会返回事件流。

测试时需要关注：

- 是否返回 `text/event-stream`。
- 是否包含 `start` 事件。
- 是否包含 `tool_call` 事件。
- 是否包含 `tool_result` 事件。
- 是否包含 `final` 事件。
- 出错时是否返回 `error` 事件。

例如：

```python
def test_chat_stream():
    with client.stream("POST", "/chat/stream", json={"message": "计算 1 + 2"}) as response:
        body = response.read().decode("utf-8")

    assert "event: start" in body
    assert "event: final" in body
```

## 17. 覆盖率是什么

覆盖率是测试执行时，有多少代码被运行过的统计指标。

常见指标包括：

- 行覆盖率：有多少行代码被执行。
- 分支覆盖率：有多少条件分支被执行。
- 函数覆盖率：有多少函数被调用。

本阶段建议核心模块测试覆盖率达到 70% 以上。

但要注意：

覆盖率高不等于测试质量高。

例如，一个测试只是执行了函数，但没有断言关键结果，也可能提高覆盖率，却不能真正保护行为。

## 18. 如何看待 70% 覆盖率

70% 是一个学习阶段比较合理的目标。

它意味着：

- 大部分核心逻辑有测试跑过。
- 关键工具和 Agent loop 至少有基本保护。
- 还有空间继续补充异常路径和边界场景。

不建议一开始追求 100%。

更好的目标是：

- 核心逻辑优先覆盖。
- 高风险路径优先覆盖。
- 常改动的模块优先覆盖。
- 纯胶水代码和简单配置可以适当放低要求。

## 19. 覆盖率工具

Python 项目中常用：

- `coverage`
- `pytest-cov`

如果安装了 `pytest-cov`，可以这样运行：

```bash
pytest --cov=app --cov-report=term-missing
```

其中：

- `--cov=app` 表示统计 `app` 目录覆盖率。
- `--cov-report=term-missing` 表示在终端显示没覆盖到的行。

报告中你会看到：

```text
Name                         Stmts   Miss  Cover   Missing
----------------------------------------------------------
app/agent/loop.py              120     24    80%   30-34, 80-90
```

`Missing` 中的行号就是没有被测试执行到的代码。

## 20. 覆盖率的误区

### 20.1 只追求数字

覆盖率 90% 但断言很弱，可能不如覆盖率 70% 但断言关键行为明确。

### 20.2 忽略异常路径

很多 bug 不发生在正常路径，而发生在：

- 参数为空。
- 类型错误。
- 工具失败。
- 模型输出异常。
- 超过最大步数。

### 20.3 把真实外部服务纳入普通测试

普通测试应该稳定、快速、便宜。

真实 LLM、真实网络、真实第三方服务应该被隔离，或者只在专门的集成测试中运行。

## 21. 测试命名

测试命名应该表达行为。

推荐：

```python
def test_chat_rejects_empty_message():
    ...
```

不推荐：

```python
def test_case_1():
    ...
```

好的测试名应该回答：

- 在什么场景下？
- 系统应该做什么？

例如：

- `test_safe_eval_rejects_function_call`
- `test_agent_respects_max_steps`
- `test_chat_returns_trace_id`
- `test_tools_endpoint_returns_registered_tools`

## 22. 测试失败信息

验收标准中提到：测试失败信息要能帮助定位问题。

这意味着断言不要太模糊。

例如：

```python
assert response.status_code == 200
```

如果失败，只知道状态码不对。

可以补充：

```python
assert response.status_code == 200, response.text
```

这样失败时可以看到响应内容。

对复杂结构，也可以先取出关键字段再断言：

```python
body = response.json()

assert body["used_tools"] == ["calculator"]
assert body["trace_id"].startswith("trace_")
```

## 23. 测试数据与 Fixture

Fixture 是测试准备数据或依赖对象的一种机制。

在 `pytest` 中，可以用 `@pytest.fixture` 定义。

例如：

```python
@pytest.fixture
def calculator_tool():
    return CalculatorTool()
```

然后在测试中使用：

```python
def test_calculator(calculator_tool):
    ...
```

Fixture 适合准备：

- 测试用工具注册表。
- mock 模型。
- 临时文件目录。
- FastAPI TestClient。
- 测试数据库。

Fixture 的价值是减少重复准备代码。

## 24. 测试隔离

测试之间应该尽量互不影响。

常见问题：

- 一个测试修改了全局变量，影响另一个测试。
- 一个测试新增了待办，另一个测试读到了这个待办。
- 一个测试创建了文件，另一个测试也使用同名文件。
- 测试依赖执行顺序。

解决方式：

- 每个测试创建自己的对象。
- 使用 fixture 管理资源。
- 使用临时目录。
- 测试结束后清理状态。
- 避免共享可变全局状态。

Agent 项目中特别要注意内存 store、工具注册表和 mock 模型状态。

## 25. 异步测试

Agent 和工具可能是异步函数。

例如：

```python
async def arun(...):
    ...
```

测试异步函数时，常用 `pytest-asyncio`：

```python
@pytest.mark.asyncio
async def test_agent_uses_calculator():
    result = await agent.run("计算 1 + 2", trace_id="trace_test")

    assert result.used_tools == ["calculator"]
```

如果忘记 `await`，测试可能不会真正执行异步逻辑。

## 26. CI 是什么

CI 是 Continuous Integration，持续集成。

它的作用是在代码提交后自动运行检查。

常见 CI 内容包括：

- 安装依赖。
- 运行测试。
- 检查格式。
- 检查类型。
- 生成覆盖率报告。

本阶段 CI 可选，但学习路线建议在阶段末尾补上。

一个最小 CI 可以只做一件事：

```text
每次 push 或 pull request 时运行 pytest
```

这样可以防止明显坏掉的代码进入主分支。

## 27. 本项目建议测试清单

为了达到“不少于 20 个测试”的最低要求，可以按下面分配。

工具层：

- calculator 正常表达式。
- calculator 一元正号。
- calculator 幂运算。
- calculator 拒绝函数调用。
- calculator 拒绝除以 0。
- file_search 找到关键词。
- file_search 找不到关键词。
- file_search 根目录不存在。
- todo 添加待办。
- todo 查看待办。
- todo 完成待办。
- todo 按 session 隔离。

Agent 层：

- 无工具时直接回答。
- 一次工具调用。
- 多次工具调用。
- 超过 `max_steps`。
- 工具失败后返回错误。
- `used_tools` 正确。
- `trace_id` 正确。

API 层：

- `/health` 成功。
- `/tools` 返回工具列表。
- `/chat` 普通消息。
- `/chat` 计算工具。
- `/chat` 空消息校验错误。
- `/chat` 超过 `max_steps`。
- `/chat/stream` 返回事件流。
- `/chat/stream` 工具调用事件。

这样总数会超过 20 个，并且覆盖比较均衡。

## 28. 本阶段验收标准

学习路线给出的验收标准包括：

- 不调用真实模型也能跑大部分测试。
- 测试失败信息能帮助定位问题。
- 你能说清哪些测试是单元测试，哪些是集成测试。

可以进一步细化为：

- 总测试数不少于 20 个。
- 核心模块覆盖率建议达到 70% 以上。
- 工具层有正常输入和异常输入测试。
- Agent loop 有 mock 模型或规则型 planner 测试。
- API 层使用 `TestClient` 测试。
- 测试可以在没有 API key 的环境中运行。
- 普通测试不依赖网络。

## 29. 学习后的自检问题

完成本子模块概念学习后，可以尝试回答：

1. 单元测试和集成测试有什么区别？
2. 为什么 Agent 测试不应该默认调用真实 LLM？
3. Mock、Stub、Fake 有什么区别？
4. 工具单元测试应该覆盖哪些类型的场景？
5. 模型输出解析为什么是高风险边界？
6. Agent loop 测试应该重点验证哪些行为？
7. FastAPI `TestClient` 解决了什么问题？
8. Streaming 接口应该如何测试？
9. 覆盖率高是否一定代表测试质量高？
10. 为什么测试之间要隔离？
11. `pytest-asyncio` 的作用是什么？
12. CI 在项目中解决什么问题？
13. 你如何判断一个测试失败信息是否足够清晰？
14. 如果只能补 5 个测试，你会优先补哪些？为什么？

## 30. 下一步实践方向

接下来做练习时，可以按下面顺序推进：

1. 查看当前 `tests/` 目录已有测试。
2. 按工具层、Agent 层、API 层分类现有测试。
3. 为工具层补充非法输入和异常路径测试。
4. 为 Agent loop 补充多工具、超过最大步数、工具失败测试。
5. 为 `/chat` 补充至少 3 个核心用例。
6. 为 `/chat/stream` 补充事件流测试。
7. 引入覆盖率工具，生成覆盖率报告。
8. 根据覆盖率报告补关键缺口，而不是盲目追求数字。
9. 有余力时添加最小 CI，让每次提交自动运行测试。

