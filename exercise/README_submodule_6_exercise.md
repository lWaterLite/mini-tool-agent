# 子模块 6 练习：测试、Mock 与覆盖率

这份文档说明子模块 6 的测试练习内容、运行方式、注意事项，以及覆盖率工具的可选配置。本文档只给出建议和示例，不会替你安装依赖或修改运行环境。

## 1. 本阶段目标

- 在子模块 5 的 FastAPI 服务化工程基础上补充测试。
- 让测试数量达到学习路线要求的 20 个以上。
- 覆盖工具层、Agent 层、API 层和 prompt 构造逻辑。
- 学习如何使用跳过测试作为后续练习题。
- 理解覆盖率工具如何配置和运行。

当前测试状态：

```text
34 passed, 3 skipped
```

其中：

- `passed` 表示已经实现并通过的测试。
- `skipped` 表示专门留下的练习测试，不影响当前测试基线。

## 2. 测试目录结构

```text
tests/
  fixtures/
    search_root/
      sample.md
  test_agent_loop.py
  test_agent_prompts.py
  test_api_chat.py
  test_exercises.py
  test_tools_calculator.py
  test_tools_file_search.py
  test_tools_registry.py
  test_tools_todo.py
  test_tools_web_summary_mock.py
```

## 3. 已补充的测试类型

### 3.1 工具层测试

工具层测试主要验证单个工具自身行为。

已覆盖：

- `calculator` 正常表达式。
- `calculator` 一元正号和幂运算。
- `calculator` 拒绝过大幂指数。
- `calculator` 拒绝除以 0。
- `calculator` 拒绝变量名。
- `calculator` 拒绝函数调用。
- `file_search` 找到关键词。
- `file_search` 找不到关键词。
- `file_search` 搜索根目录不存在。
- `todo` 添加和查看待办。
- `todo` 完成待办。
- `todo` 按 `session_id` 隔离。
- `todo` 拒绝缺少内容的新增请求。
- `web_summary_mock` 返回稳定 mock 结果。
- `web_summary_mock` 拒绝非法 URL。
- `ToolRegistry` 注册、重复注册、未知工具错误。

### 3.2 Agent 层测试

Agent 层测试主要验证 Agent loop 的流程行为。

已覆盖：

- Agent 调用计算器。
- Agent 尊重 `max_steps`。
- Todo 按 session 隔离。
- 多工具按顺序执行。
- 文件搜索缺少关键词时返回澄清回答。
- URL 输入触发网页摘要 mock 工具。

### 3.3 API 层测试

API 层测试使用 FastAPI `TestClient`。

已覆盖：

- `GET /health`
- `GET /tools`
- `POST /chat` 普通对话。
- `POST /chat` 调用计算器。
- `POST /chat` 使用 todo 和 `session_id`。
- `POST /chat` 拒绝非法 `max_steps` 类型。
- `POST /chat` 拒绝超过步数限制的请求。
- `POST /chat` 空消息校验错误。
- `POST /chat/stream` 返回事件流。

### 3.4 Prompt 测试

已覆盖：

- `build_tool_prompt` 是否包含工具名称。
- 是否包含参数 schema。
- 是否包含关键参数字段。

## 4. 运行测试

在 `mini-tool-agent` 根目录下运行：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

如果你已经激活虚拟环境，也可以运行：

```bash
pytest
```

运行单个测试文件：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_chat.py
```

运行某一个测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_chat.py::test_chat_with_calculator
```

显示更详细输出：

```powershell
.\.venv\Scripts\python.exe -m pytest -vv
```

## 5. 跳过的练习测试

`tests/test_exercises.py` 中保留了 3 个跳过测试。

它们的作用不是当前就通过，而是作为后续练习题。

### 5.1 streaming 错误事件

目标：

- 让 `/chat/stream` 在工具失败时返回 `event: error`。
- 响应体中包含错误码、错误消息和 `trace_id`。

练习文件：

```text
tests/test_exercises.py::test_exercise_stream_returns_error_event_when_tool_fails
```

### 5.2 工具超时

目标：

- 为工具执行增加超时保护。
- 工具超时时转换成统一 `AppError`。

练习文件：

```text
tests/test_exercises.py::test_exercise_agent_converts_tool_timeout_to_app_error
```

### 5.3 LLM Planner Mock 测试

目标：

- 不调用真实 LLM。
- 使用 mock 模型输出固定 JSON。
- 测试 planner 是否能解析工具计划。

练习文件：

```text
tests/test_exercises.py::test_exercise_llm_planner_uses_mock_model_output
```

当你准备实现某个练习时，可以把对应测试上的：

```python
@pytest.mark.skip(...)
```

暂时删除，然后补充测试内容和业务代码。

## 6. 覆盖率工具说明

当前我没有替你安装覆盖率依赖，也没有直接修改你的环境。

如果你想学习覆盖率，可以自行选择是否安装 `pytest-cov`。

### 6.1 可选依赖

你可以手动安装：

```powershell
uv add pytest-cov
```

或者：

```powershell
.\.venv\Scripts\python.exe -m pip install pytest-cov
```

选择哪种方式取决于你希望如何管理依赖。

### 6.2 可选 pyproject 配置

如果你希望把覆盖率配置写进 `pyproject.toml`，可以手动添加：

```toml
[tool.coverage.run]
source = ["app"]

[tool.coverage.report]
show_missing = true
skip_covered = true
```

这段配置表示：

- 只统计 `app` 目录。
- 显示未覆盖行。
- 已完全覆盖的文件可以简略显示。

### 6.3 运行覆盖率

安装 `pytest-cov` 后，可以运行：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
```

也可以生成 HTML 报告：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=html
```

生成后通常会出现：

```text
htmlcov/
```

打开其中的 `index.html` 可以查看图形化覆盖率报告。

## 7. 阅读测试建议

建议按下面顺序阅读：

1. `tests/test_tools_calculator.py`
2. `tests/test_tools_file_search.py`
3. `tests/test_tools_todo.py`
4. `tests/test_tools_registry.py`
5. `tests/test_agent_loop.py`
6. `tests/test_api_chat.py`
7. `tests/test_exercises.py`

这样顺序是从单元测试到集成测试，再到后续练习。

## 8. 注意事项

- 普通测试不要调用真实 LLM。
- 普通测试不要依赖外部网络。
- 测试之间不要共享可变状态。
- API 测试可以使用 `TestClient`，不需要启动真实服务。
- 异步函数测试需要 `pytest.mark.asyncio`。
- 跳过测试是练习入口，不是失败。
- 覆盖率是辅助指标，不要只追求数字。

## 9. 后续练习建议

- 为 `/chat/stream` 增加错误事件测试。
- 为工具执行增加超时测试。
- 为未来的真实 LLM planner 增加 mock 测试。
- 为错误响应补充更多断言。
- 为 `Settings.from_env()` 增加配置读取测试。
- 为 `FileSearchTool` 增加忽略目录和多行匹配测试。
- 使用覆盖率报告找出未测试的关键分支。

