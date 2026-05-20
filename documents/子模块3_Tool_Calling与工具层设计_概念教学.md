# 子模块 3：Tool Calling 与工具层设计概念教学

对应学习路线：模块 1「LLM 工程基础与最小 Agent」  
学习主题：Tool Calling、工具 schema、参数校验、工具执行、工具返回、工具注册与四类基础工具设计

---

## 1. 本节学习目标

完成本节后，你应该能够：

1. 理解 agent 调用工具的基本过程。
2. 解释 tool calling 和普通 LLM chat 的区别。
3. 设计工具 schema，让模型知道工具名称、用途和参数结构。
4. 使用 Pydantic 对工具参数进行校验。
5. 将每个工具封装成可测试、可替换的 Python 函数或类。
6. 设计统一的工具返回结构，例如 `ToolResult`。
7. 理解工具失败时为什么不能让整个 agent 直接崩溃。
8. 初步设计计算器、文件检索、网页摘要 mock、待办事项四类工具。

这一节的核心是：**不要让模型直接做所有事情，而是让模型决定什么时候调用确定性代码。**

---

## 2. 从普通 Chat 到 Tool Calling

### 普通 Chat

普通 chat 是模型直接根据上下文生成回答：

```text
用户：帮我计算 19 * 23 + 7
模型：19 * 23 + 7 = 444
```

这里模型自己“心算”。它可能算对，也可能算错。

### Tool Calling

Tool calling 是模型不直接完成所有任务，而是先判断是否需要工具，再输出工具调用请求：

```text
用户：帮我计算 19 * 23 + 7
模型：需要调用 calculator 工具，参数是 expression = "19 * 23 + 7"
程序：执行 calculator 工具
工具：返回 444
模型：根据工具结果回答用户
```

### 核心区别

```text
普通 Chat：模型直接回答
Tool Calling：模型负责决策，工具负责执行
```

工具调用把不稳定的自然语言生成和稳定的程序执行分开了。

---

## 3. Agent 为什么需要工具

LLM 擅长：

- 理解自然语言。
- 判断用户意图。
- 生成解释。
- 整合上下文。
- 选择下一步行动。

LLM 不擅长或不应该直接做：

- 精确计算。
- 读取本地文件。
- 访问数据库。
- 修改待办事项。
- 调用外部 API。
- 执行任意代码。

工具的作用是把这些确定性、可控、可测试的能力交给程序。

一句话记忆：

```text
模型负责“想做什么”，工具负责“真的去做”。
```

---

## 4. Tool Calling 的基本过程

最小工具调用流程：

```text
用户输入
-> 构造 messages
-> 模型判断是否需要工具
-> 模型输出工具名称和参数
-> 程序校验工具名称
-> 程序校验工具参数
-> 执行工具函数
-> 得到工具结果
-> 把工具结果交回模型
-> 模型生成最终回答
```

在子模块 3 中，你先重点学习工具层本身：

```text
工具名称
工具描述
参数 schema
参数校验
工具执行
统一返回
错误处理
测试
```

真正完整的 agent loop 会在子模块 4 中实现。

---

## 5. 工具是什么

### 定义

工具是 agent 可以调用的外部能力。它通常是一个 Python 函数或类，接收结构化参数，返回结构化结果。

例如计算器工具：

```python
def calculator(expression: str) -> ToolResult:
    ...
```

文件检索工具：

```python
def file_search(query: str, directory: str) -> ToolResult:
    ...
```

### 工具的组成

一个工程化工具通常包含：

- `name`：工具名称。
- `description`：工具描述。
- `args_model`：参数 Pydantic model。
- `run`：实际执行函数。
- `result_model`：返回结构。

### 工具不是 prompt

工具不是一段自然语言说明。  
工具是可执行代码，必须有明确输入、明确输出和可测试行为。

---

## 6. 工具 Schema

### 定义

工具 schema 是对工具的结构化描述，告诉模型和程序：

- 工具叫什么。
- 工具能做什么。
- 需要哪些参数。
- 参数类型是什么。
- 哪些参数必填。

示例：

```json
{
  "name": "calculator",
  "description": "计算安全的数学表达式，支持加减乘除和括号。",
  "parameters": {
    "type": "object",
    "properties": {
      "expression": {
        "type": "string",
        "description": "要计算的数学表达式，例如 19 * 23 + 7"
      }
    },
    "required": ["expression"]
  }
}
```

### 作用

工具 schema 的作用是降低模型和工具之间的沟通成本。

模型通过 schema 知道：

- 什么场景可以用这个工具。
- 应该输出什么参数。
- 参数应该如何命名。

程序通过 schema 知道：

- 如何校验参数。
- 如何向 `/tools` 接口展示工具。
- 如何做自动文档。

---

## 7. Pydantic 参数模型

### 定义

工具参数模型是用于描述工具输入参数的 Pydantic `BaseModel`。

示例：

```python
from pydantic import BaseModel, Field


class CalculatorArgs(BaseModel):
    expression: str = Field(
        min_length=1,
        description="要计算的数学表达式，例如 19 * 23 + 7",
    )
```

### 作用

参数模型可以：

- 拦截缺失参数。
- 拦截类型错误。
- 限制字符串长度。
- 限制路径范围。
- 生成 JSON schema。
- 让测试更直接。

### 为什么工具参数必须校验

因为工具会执行真实代码。如果参数不校验，可能出现：

- 计算器执行危险代码。
- 文件检索读取项目外文件。
- 待办事项写入错误结构。
- 工具异常让 agent 崩溃。

模型输出永远不能直接信任，必须经过参数校验。

---

## 8. 工具执行

### 定义

工具执行是指程序根据工具名称找到对应工具，并用通过校验的参数调用它。

示例流程：

```python
args = CalculatorArgs.model_validate(raw_args)
result = run_calculator(args)
```

### 工程要求

工具执行应该满足：

- 输入明确。
- 输出明确。
- 不依赖全局混乱状态。
- 失败时返回错误，而不是直接崩溃。
- 可以被单元测试独立调用。

### 模型不能直接执行工具

模型只能“请求调用工具”。  
真正执行工具的必须是你的程序。

这能保证：

- 工具白名单可控。
- 参数可校验。
- 权限可限制。
- 错误可捕获。
- 日志可追踪。

---

## 9. ToolResult

### 定义

`ToolResult` 是统一工具返回结构。学习路线建议：

```python
class ToolResult(BaseModel):
    ok: bool
    content: str
    data: dict | None = None
    error: str | None = None
```

### 字段含义

`ok`：工具是否执行成功。  
成功为 `True`，失败为 `False`。

`content`：给模型或用户看的简短文本结果。  
例如 `"计算结果是 444"`。

`data`：给程序使用的结构化数据。  
例如 `{"value": 444}`。

`error`：失败时的错误说明。  
例如 `"表达式包含不允许的字符"`。

### 为什么需要统一返回

如果每个工具返回格式不同，agent loop 会非常难写。

统一返回可以让后续流程简单很多：

```python
if result.ok:
    ...
else:
    ...
```

---

## 10. 工具失败处理

### 常见失败

工具可能因为很多原因失败：

- 参数缺失。
- 参数类型错误。
- 工具名称不存在。
- 表达式不合法。
- 文件路径越权。
- 文件不存在。
- 数据存储损坏。
- 外部 API 超时。

### 处理原则

工具失败时，不应该让整个 agent 直接崩溃。

更好的做法是返回：

```python
ToolResult(
    ok=False,
    content="工具执行失败。",
    error="表达式包含不允许的字符",
)
```

然后由 agent 决定：

- 向用户解释失败原因。
- 要求模型重新选择工具。
- 要求用户补充参数。
- 进入兜底回答。

---

## 11. 工具注册表

### 定义

工具注册表是保存所有可用工具的地方。它通常是一个字典或类。

示例：

```python
TOOLS = {
    "calculator": calculator_tool,
    "file_search": file_search_tool,
    "web_summary_mock": web_summary_tool,
    "todo": todo_tool,
}
```

### 作用

工具注册表负责：

- 根据工具名查找工具。
- 防止调用不存在的工具。
- 限制工具白名单。
- 输出 `/tools` 列表。
- 让工具可替换、可测试。

### 为什么需要白名单

模型不能随便调用任意函数。  
它只能调用你注册过、允许调用的工具。

否则会带来安全风险，例如：

- 执行任意 Python 代码。
- 读取任意本地文件。
- 修改系统状态。
- 泄露敏感信息。

---

## 12. 计算器工具

### 目标

计算器工具需要支持：

- 加法
- 减法
- 乘法
- 除法
- 括号
- 简单数学表达式

示例：

```text
19 * 23 + 7
(10 + 5) / 3
```

### 关键风险

不能直接使用：

```python
eval(expression)
```

因为用户或模型可能传入危险表达式：

```python
__import__("os").system("del important_file")
```

### 推荐思路

安全计算器可以使用 Python 的 `ast` 模块解析表达式，只允许特定节点：

- 数字
- 加减乘除
- 一元正负号
- 括号对应的表达式树

如果出现函数调用、属性访问、导入语句、变量名，就拒绝。

### 工具参数

```python
class CalculatorArgs(BaseModel):
    expression: str
```

### 返回示例

```python
ToolResult(
    ok=True,
    content="计算结果是 444",
    data={"value": 444},
)
```

---

## 13. 文件检索工具

### 目标

文件检索工具需要：

- 在指定目录内搜索 `.md` 或 `.txt` 文件。
- 返回文件名。
- 返回匹配行。
- 返回上下文片段。
- 不允许读取项目目录外文件。

### 参数示例

```python
class FileSearchArgs(BaseModel):
    query: str
    directory: str
    max_results: int = 5
```

### 安全边界

文件检索工具最重要的是路径安全。

必须防止：

```text
../../secret.txt
C:/Users/xxx/private.txt
```

基本思路：

```python
root = Path(project_root).resolve()
target = (root / directory).resolve()

if not target.is_relative_to(root):
    raise ValueError("不允许读取项目目录外文件")
```

### 返回结构

可以返回：

```python
ToolResult(
    ok=True,
    content="找到 2 条匹配结果。",
    data={
        "matches": [
            {
                "file": "notes/rag.md",
                "line": 12,
                "snippet": "RAG evaluation 需要关注 recall..."
            }
        ]
    },
)
```

---

## 14. 网页摘要 Mock 工具

### 目标

本阶段暂时不接真实浏览器，也不做真实网页抓取。  
网页摘要工具先做 mock：

```text
给定 URL
-> 返回预设摘要或 mock 数据
```

### 为什么先做 mock

因为本阶段重点是工具接口，不是网页抓取。

mock 工具有几个好处：

- 不依赖网络。
- 测试稳定。
- 不受网页变化影响。
- 先练习外部工具返回结构。
- 后续可以替换成真实网页加载器。

### 参数示例

```python
class WebSummaryArgs(BaseModel):
    url: str
```

### 返回示例

```python
ToolResult(
    ok=True,
    content="该网页介绍了 AI Agent 的基本概念。",
    data={
        "url": "https://example.com/agent-intro",
        "summary": "AI Agent 可以根据目标调用工具完成任务。"
    },
)
```

---

## 15. 待办事项管理工具

### 目标

待办工具需要支持：

- 新增任务。
- 查看任务。
- 完成任务。

### 初期存储方式

可以先使用：

- 内存列表。
- 本地 JSON 文件。

后续再替换为：

- SQLite。
- 后端数据库。
- 外部任务管理服务。

### 参数设计

可以先拆成多个 action：

```python
class TodoArgs(BaseModel):
    action: Literal["add", "list", "complete"]
    title: str | None = None
    task_id: str | None = None
```

跨字段约束：

- `action == "add"` 时，必须有 `title`。
- `action == "complete"` 时，必须有 `task_id`。
- `action == "list"` 时，不需要额外参数。

### 返回示例

```python
ToolResult(
    ok=True,
    content="已添加待办：周五整理 mini-tool-agent README。",
    data={
        "task": {
            "id": "1",
            "title": "周五整理 mini-tool-agent README",
            "done": False
        }
    },
)
```

---

## 16. 工具函数 vs 工具类

### 工具函数

函数适合简单工具：

```python
def run_calculator(args: CalculatorArgs) -> ToolResult:
    ...
```

优点：

- 简单。
- 易测试。
- 适合无状态工具。

### 工具类

类适合需要配置或状态的工具：

```python
class TodoTool:
    def __init__(self, store_path: Path):
        self.store_path = store_path

    def run(self, args: TodoArgs) -> ToolResult:
        ...
```

优点：

- 可以注入配置。
- 可以管理状态。
- 可以替换存储实现。

### 本阶段建议

本阶段可以采用折中方案：

- 工具核心逻辑用函数。
- 用一个轻量 `ToolSpec` 或工具注册表管理名称、描述和参数 model。
- 待办事项工具如果使用 JSON 文件，可以用类管理路径。

---

## 17. 可测试、可替换是什么意思

### 可测试

工具应该能独立测试，不依赖真实模型。

例如计算器测试：

```python
def test_calculator_addition():
    args = CalculatorArgs(expression="1 + 2")
    result = run_calculator(args)
    assert result.ok is True
    assert result.data["value"] == 3
```

### 可替换

工具实现可以替换，但接口不变。

例如网页摘要工具：

```text
现在：mock 返回预设摘要
以后：真实抓取网页并总结
```

只要输入和输出结构不变，agent loop 不需要大改。

---

## 18. 工具层和 Agent Loop 的边界

工具层负责：

- 定义工具。
- 校验参数。
- 执行工具。
- 返回 `ToolResult`。
- 捕获工具内部错误。

Agent loop 负责：

- 接收用户任务。
- 调用模型。
- 解析模型决策。
- 选择工具。
- 把工具结果加入 messages。
- 决定是否继续循环。
- 生成最终回答。

不要把这两层混在一起。  
工具层越干净，后续 agent loop 越容易写和测试。

---

## 19. 本节常见误区

### 误区 1：让模型直接算结果

简单计算模型可能算对，但不稳定。  
计算应该交给确定性代码。

### 误区 2：工具参数不校验

模型输出不能直接进入工具执行。  
参数必须先经过 Pydantic 或等价校验。

### 误区 3：计算器直接用 eval

`eval` 风险很高。  
即使只是学习项目，也应该从一开始建立安全边界。

### 误区 4：文件检索不限制目录

这会造成越权读取风险。  
文件工具必须限制在项目允许目录内。

### 误区 5：每个工具返回不同结构

这会让 agent loop 很难统一处理。  
应该统一使用 `ToolResult`。

### 误区 6：工具失败直接抛到最外层

工具失败是正常情况。  
失败应该被捕获并转换成结构化错误结果。

---

## 20. 复习小抄

| 概念 | 一句话理解 | 工程作用 |
| --- | --- | --- |
| Tool Calling | 模型请求程序调用工具 | 把决策和执行分开 |
| 工具 | agent 可调用的外部能力 | 提供确定性、可控能力 |
| 工具 schema | 工具名称、描述和参数结构 | 让模型和程序知道如何调用 |
| 参数校验 | 检查工具输入是否合法 | 防止错误和危险输入进入工具 |
| Pydantic 参数模型 | 用 BaseModel 定义工具参数 | 自动校验和生成 schema |
| 工具执行 | 调用真实 Python 函数或类 | 完成计算、搜索、存储等动作 |
| ToolResult | 统一工具返回格式 | 让 agent loop 统一处理结果 |
| 工具注册表 | 保存可用工具的集合 | 支持白名单、查找和 `/tools` |
| 工具白名单 | 只允许调用注册工具 | 降低安全风险 |
| 计算器工具 | 安全计算表达式 | 避免模型算错，禁止任意代码 |
| 文件检索工具 | 搜索指定目录文本文件 | 支持本地知识查找，限制越权 |
| 网页摘要 mock | 模拟外部网页摘要 | 不依赖网络，练习工具接口 |
| 待办事项工具 | 新增、查看、完成任务 | 练习状态变更型工具 |
| 可测试 | 不依赖真实模型也能测工具 | 提升稳定性 |
| 可替换 | 实现可换，接口不变 | 方便后续扩展 |

---

## 21. 学完后的自检问题

1. Tool calling 和普通 chat 的区别是什么？
2. 为什么模型不应该直接执行任意 Python 代码？
3. 工具 schema 应该包含哪些信息？
4. 为什么工具参数必须做校验？
5. 为什么计算器工具不应该直接使用 `eval`？
6. 文件检索工具如何避免读取项目目录外文件？
7. `ToolResult.ok`、`content`、`data`、`error` 分别有什么作用？
8. 工具失败时为什么不应该让整个 agent 直接崩溃？
9. 网页摘要工具为什么本阶段先做 mock？
10. 工具层和 agent loop 的职责边界是什么？

---

## 22. 下一步实践

下一步可以开始实现子模块 3 的小练习：

```text
1. 定义通用工具返回：
   - ToolResult

2. 为每个工具定义参数模型：
   - CalculatorArgs
   - FileSearchArgs
   - WebSummaryArgs
   - TodoArgs

3. 实现计算器工具：
   - 支持加减乘除和括号
   - 禁止任意 Python 代码

4. 实现文件检索工具：
   - 只搜索 .md 和 .txt
   - 返回文件、行号、片段
   - 限制在项目目录内

5. 实现网页摘要 mock 工具：
   - 给定 URL
   - 返回预设摘要

6. 实现待办事项工具：
   - 新增
   - 查看
   - 完成

7. 实现工具注册表：
   - 根据名称查找工具
   - 列出可用工具
   - 拒绝不存在的工具

8. 为每个工具写独立测试：
   - 正常输入
   - 非法输入
   - 工具失败
```

完成这部分后，你就具备了进入子模块 4 的基础：让 agent loop 根据模型决策调用这些工具，并把工具结果交回模型生成最终回答。
