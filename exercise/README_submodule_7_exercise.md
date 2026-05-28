# 子模块 7 练习：日志、配置、Docker 与 README

这份文档对应模块 1 的最后一个子模块。目标是把 `mini-tool-agent` 从“代码能跑”整理成一个更容易展示、复现和排查问题的小型工程。

本练习已经补充了部分工程实践，同时保留了一些后续练习题。本文档只说明需要做什么、如何运行、如何验证；不会要求你必须立即安装依赖或修改本地环境。

## 1. 本阶段目标

- 配置管理：用 `.env.example` 和 `Settings` 统一管理环境变量。
- 结构化日志：让一次 Agent 工具调用可以通过 `trace_id` 复盘。
- Docker：提供本地构建和启动 API 的容器化文件。
- README：说明项目背景、运行方法、测试方法、限制和后续计划。

## 2. 本次新增或修改的文件

```text
app/core/config.py
app/core/logging.py
app/agent/loop.py
.env.example
.gitignore
.dockerignore
Dockerfile
docker-compose.yml
exercise/README_submodule_7.md
```

## 3. 配置管理

当前配置入口是：

```text
app/core/config.py
```

核心类是：

```python
Settings
```

它负责从环境变量读取：

- `APP_NAME`
- `APP_ENV`
- `APP_DEBUG`
- `LOG_LEVEL`
- `FILE_SEARCH_ROOT`
- `MAX_FILE_SEARCH_RESULTS`
- `MAX_AGENT_STEPS`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `LLM_TEMPERATURE`
- `LLM_MAX_TOKENS`

新增的辅助函数：

- `_int_from_env`
- `_float_from_env`

它们用于把环境变量转换成正确类型。如果用户写了非法值，会在启动时暴露配置错误。

### 练习 1：继续整理工具配置

现在 `.env.example` 中预留了：

```env
CALCULATOR_MAX_POWER_EXPONENT=8
```

请尝试把它真正接入：

1. 新增 `CalculatorSettings`。
2. 让 `Settings` 持有 `calculator: CalculatorSettings`。
3. 让 `CalculatorTool` 接收 `CalculatorSettings`。
4. 把最大幂指数从硬编码改成配置。
5. 为配置读取和计算器限制补测试。

思考：

- 工具应该接收整个 `Settings`，还是只接收自己的配置对象？
- 如果配置非法，应该启动失败还是使用默认值？

## 4. 结构化日志

当前结构化日志入口是：

```text
app/core/logging.py
```

新增函数：

```python
log_event(logger, level, event, **fields)
summarize_text(text, max_length=80)
```

`log_event` 会把日志正文输出为 JSON 字符串。这样后续可以通过字段搜索：

- `event`
- `trace_id`
- `tool_name`
- `latency_ms`
- `final_status`

### 4.1 当前会记录的事件

在 `app/agent/loop.py` 中，当前记录了：

- `request_started`
- `agent_plan_created`
- `request_rejected`
- `tool_call_started`
- `tool_call_finished`
- `tool_call_failed`
- `request_finished`

一次成功计算请求大致会产生：

```text
request_started
agent_plan_created
tool_call_started
tool_call_finished
request_finished
```

一次工具失败请求大致会产生：

```text
request_started
agent_plan_created
tool_call_started
tool_call_failed
```

### 4.2 日志字段

当前日志包含的核心字段：

- `trace_id`
- `session_id`
- `message_preview`
- `message_length`
- `planned_tools`
- `tool_name`
- `tool_arguments`
- `latency_ms`
- `status`
- `error_code`
- `error_message`
- `final_status`
- `used_tools`

### 练习 2：补齐失败请求的最终状态日志

当前工具失败时已经记录 `tool_call_failed`，但你可以继续增强：

- 在工具失败后补一条 `request_finished`。
- `final_status` 设置为 `error`。
- 记录 `error_code` 和 `used_tools`。

思考：

- 这段逻辑应该写在 `AgentService.stream` 里，还是写成统一的 helper？

### 练习 3：日志脱敏

当前 `tool_arguments` 会直接进入日志。

请尝试实现一个简单脱敏函数：

```python
sanitize_for_log(data: dict) -> dict
```

要求：

- 如果 key 中包含 `key`、`token`、`password`，值替换为 `"***"`。
- 对过长字符串做截断。
- 对嵌套 dict 做递归处理。

思考：

- 用户输入和工具参数是否都应该完整写日志？

## 5. Docker 文件

本次新增：

```text
Dockerfile
.dockerignore
docker-compose.yml
```

### 5.1 Dockerfile

当前 Dockerfile 主要步骤：

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2 .dockerignore

`.dockerignore` 会排除：

- `.env`
- `.venv`
- `.git`
- 缓存目录
- 覆盖率报告
- 本地 IDE 配置

重点是不要把 `.env` 和本地虚拟环境打进镜像。

### 5.3 docker-compose.yml

`docker-compose.yml` 是可选实践，当前只定义一个 API 服务。

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
```

### Docker 运行命令

如果你想自己验证 Docker，可以手动执行：

```powershell
docker build -t mini-tool-agent .
```

```powershell
docker run --env-file .env -p 8000:8000 mini-tool-agent
```

或者：

```powershell
docker compose up --build
```

本次我不会替你执行这些命令。

### 练习 4：优化 Dockerfile

当前 Dockerfile 是学习版，可以继续优化：

- 使用非 root 用户运行。
- 单独复制依赖文件，提高构建缓存命中。
- 增加 healthcheck。
- 只安装运行时依赖，不安装测试依赖。

思考：

- 为什么 `.env` 不应该 `COPY` 到镜像里？
- Docker 镜像和容器分别是什么？

## 6. README 要求

子模块 7 要求 README 能让别人快速理解项目。

建议根 README 至少包含：

- 项目背景。
- 架构图或流程图。
- 快速启动。
- API 示例。
- 工具列表。
- 测试方式。
- Docker 运行方式。
- 日志说明。
- 已知限制。
- 下一步计划。

### 练习 5：重写根 README

请尝试基于当前项目重新写根目录 `README.md`。

建议结构：

```text
1. 项目简介
2. 功能特性
3. 架构图
4. 快速启动
5. 配置说明
6. API 示例
7. 工具列表
8. 日志说明
9. 测试方式
10. Docker 运行
11. 已知限制
12. 下一步计划
```

思考：

- 如果面试官只有 3 分钟，你希望他先看到什么？
- README 中应该展示实现细节，还是展示项目价值？

## 7. 验证方式

### 7.1 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### 7.2 观察日志

启动服务后调用：

```powershell
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"计算 3 * (4 + 5)\"}"
```

观察控制台日志中是否能看到：

- `request_started`
- `agent_plan_created`
- `tool_call_started`
- `tool_call_finished`
- `request_finished`

并确认这些日志共享同一个 `trace_id`。

### 7.3 检查 Docker 文件

你可以自己执行：

```powershell
docker build -t mini-tool-agent .
```

本练习不会自动执行 Docker 构建。

## 8. 注意事项

- 不要提交真实 `.env`。
- 不要把 API key 写入日志。
- 不要把完整异常栈返回给用户。
- Docker 镜像不应该包含 `.venv`。
- `.dockerignore` 和 `.gitignore` 解决的是不同问题。
- 结构化日志是为了排查问题，不是为了记录所有数据。
- README 是项目交付物，不是附属品。

## 9. 子模块 7 自检问题

1. 为什么配置入口应该集中在 `Settings`？
2. 为什么 `.env.example` 可以提交，而 `.env` 不应该提交？
3. 为什么日志里需要 `trace_id`？
4. 工具调用日志为什么要记录耗时？
5. 哪些字段不适合直接写入日志？
6. Dockerfile 解决了什么问题？
7. `.dockerignore` 和 `.gitignore` 有什么区别？
8. README 如何帮助别人复现项目？
9. 如果工具调用失败，你应该如何从日志复盘？
10. 当前项目离真实部署还缺哪些能力？

