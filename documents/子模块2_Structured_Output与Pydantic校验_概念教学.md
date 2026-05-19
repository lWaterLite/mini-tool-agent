# 子模块 2：Structured Output 与 Pydantic 校验概念教学

对应学习路线：模块 1「LLM 工程基础与最小 Agent」  
学习主题：结构化输出、JSON schema、Pydantic 校验、输出解析、失败重试与错误消息设计

---

## 1. 本节学习目标

完成本节后，你应该能够：

1. 解释结构化输出和普通文本输出的区别。
2. 让模型尽量输出固定结构的 JSON。
3. 使用 Pydantic `BaseModel` 描述模型输出结构。
4. 使用字段约束限制字段类型、范围、枚举值和默认值。
5. 解析模型输出，并处理 JSON 解析失败、字段缺失和类型错误。
6. 设计清晰的校验错误消息，并把错误反馈给模型进行一次重试。
7. 为输出解析器编写单元测试。

这一节的核心不是“让模型看起来输出 JSON”，而是建立一条工程链路：

```text
自然语言任务
-> prompt 约束模型输出结构
-> 获取模型原始输出
-> JSON 解析
-> Pydantic 校验
-> 合法结果进入后续逻辑
-> 不合法结果触发错误处理或重试
```

---

## 2. 为什么需要 Structured Output

### 普通文本输出的问题

普通 LLM 回复通常是自然语言，例如：

```text
用户想要搜索文件，关键词是 RAG evaluation。我觉得需要调用工具。
```

这对人类很友好，但对程序不友好。程序很难稳定判断：

- 用户意图到底是什么？
- 参数在哪里？
- 是否需要工具？
- 置信度是多少？
- 模型有没有额外说废话？

如果你用字符串搜索去判断：

```python
if "需要调用工具" in text:
    ...
```

系统会非常脆弱。模型只要换一种说法，例如“建议使用工具”，你的逻辑就可能失效。

### 结构化输出的目标

结构化输出希望模型直接给出程序容易解析的结构，例如：

```json
{
  "intent": "file_search",
  "arguments": {
    "keyword": "RAG evaluation",
    "directory": "notes"
  },
  "confidence": 0.86,
  "need_tool": true
}
```

这样程序就可以明确读取：

```python
intent = result.intent
arguments = result.arguments
need_tool = result.need_tool
```

### 工程价值

结构化输出的价值在于：

- 降低模型输出的不确定性。
- 让下游代码更容易处理。
- 让测试更容易编写。
- 让 agent 决策过程更清晰。
- 让错误能被定位和恢复。

一句话记忆：

```text
普通文本输出适合给人看，结构化输出适合给程序用。
```

---

## 3. Structured Output

### 定义

Structured Output 指模型按照预先定义的结构输出结果，常见形式是 JSON。

它不只是“输出一段长得像 JSON 的文本”，而是要求输出满足明确字段、类型和约束。

例如子模块 2 的练习目标是让模型把用户任务解析成：

```json
{
  "intent": "calculator",
  "arguments": {
    "expression": "19 * 23 + 7"
  },
  "confidence": 0.95,
  "need_tool": true
}
```

### 作用

在 agent 项目中，结构化输出常用于：

- 意图识别：判断用户想做什么。
- 参数抽取：从自然语言中提取工具参数。
- 工具选择：判断是否需要调用工具。
- 路由决策：决定进入哪个处理分支。
- 风险判断：判断是否需要拒绝、澄清或重试。
- 最终 API 响应：返回稳定的 JSON 给前端。

### 注意点

结构化输出仍然可能失败。模型可能输出：

- 非 JSON 文本。
- JSON 前后带解释文字。
- 字段缺失。
- 字段类型错误。
- 多余字段。
- 布尔值写成字符串。
- 数字范围不合法。
- 枚举值不在允许范围内。

所以结构化输出必须配合解析和校验。

---

## 4. JSON

### 定义

JSON 是一种轻量级数据格式，全称是 JavaScript Object Notation。它常用于 API 请求、响应和配置文件。

常见 JSON 结构：

```json
{
  "intent": "todo_add",
  "arguments": {
    "title": "周五整理 README"
  },
  "confidence": 0.91,
  "need_tool": true
}
```

### 常见类型

JSON 支持这些基本类型：

- object：对象，例如 `{ "name": "Alice" }`
- array：数组，例如 `[1, 2, 3]`
- string：字符串，例如 `"hello"`
- number：数字，例如 `0.9`
- boolean：布尔值，例如 `true`、`false`
- null：空值

### Python 中的对应关系

```text
JSON object  -> Python dict
JSON array   -> Python list
JSON string  -> Python str
JSON number  -> Python int 或 float
JSON boolean -> Python bool
JSON null    -> Python None
```

### 工程注意点

严格 JSON 里：

- 字符串必须使用双引号。
- 布尔值是 `true` / `false`，不是 Python 的 `True` / `False`。
- 不能有尾随逗号。
- 不能写注释。

下面不是合法 JSON：

```text
{
  intent: "calculator",
  "need_tool": True,
}
```

---

## 5. JSON Schema

### 定义

JSON Schema 是描述 JSON 数据结构的规则。它可以说明一个 JSON 对象应该有哪些字段、字段是什么类型、是否必填、取值范围是什么。

示例：

```json
{
  "type": "object",
  "properties": {
    "intent": {
      "type": "string"
    },
    "arguments": {
      "type": "object"
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    },
    "need_tool": {
      "type": "boolean"
    }
  },
  "required": ["intent", "arguments", "confidence", "need_tool"]
}
```

### 作用

JSON Schema 的作用是把“希望模型输出什么结构”说清楚：

- 哪些字段必须存在。
- 字段类型是什么。
- 数字范围是什么。
- 字符串是否只能从几个值里选。
- 是否允许额外字段。

### 和 Pydantic 的关系

Pydantic model 可以生成 JSON schema，也可以根据 schema 思想来校验数据。

你可以把二者理解成：

```text
JSON Schema：描述数据结构的通用标准
Pydantic：Python 里定义、校验和使用结构化数据的工具
```

在 agent 工程中，Pydantic 更常作为代码中的“强约束层”。

---

## 6. Pydantic

### 定义

Pydantic 是 Python 中常用的数据校验和类型管理库。它可以根据类型注解检查输入数据是否符合预期，并把合法数据转换成 Python 对象。

示例：

```python
from pydantic import BaseModel


class TaskIntent(BaseModel):
    intent: str
    arguments: dict
    confidence: float
    need_tool: bool
```

如果输入合法：

```python
data = {
    "intent": "calculator",
    "arguments": {"expression": "19 * 23 + 7"},
    "confidence": 0.95,
    "need_tool": True,
}

parsed = TaskIntent.model_validate(data)
```

那么 `parsed` 就是一个有类型的对象：

```python
parsed.intent
parsed.arguments
parsed.need_tool
```

### 作用

Pydantic 在 agent 工程中的价值很大：

- 把模型输出从“字符串”变成“可靠对象”。
- 拦截字段缺失。
- 拦截类型错误。
- 拦截不合法取值。
- 统一错误格式。
- 让测试更容易写。
- 让后续工具调用更安全。

### 为什么不用普通 dict

普通 dict 很灵活，但太容易出错：

```python
intent = data["intent"]
confidence = data["confidence"]
```

如果模型少输出了字段，程序会在运行时崩溃。  
如果 `confidence` 是字符串 `"high"`，后续比较大小时也会出错。

Pydantic 可以把这些问题提前暴露出来。

---

## 7. BaseModel

### 定义

`BaseModel` 是 Pydantic 中定义数据模型的基础类。你通过继承它来声明数据结构。

示例：

```python
from pydantic import BaseModel


class AgentAction(BaseModel):
    intent: str
    arguments: dict
    confidence: float
    need_tool: bool
```

### 作用

`BaseModel` 提供：

- 字段声明。
- 类型校验。
- 默认值。
- 字段约束。
- 错误收集。
- 对象序列化。
- JSON schema 生成。

### 常见方法

不同 Pydantic 版本的 API 细节会有差异。以 Pydantic v2 风格为例，常见方法包括：

```python
AgentAction.model_validate(data)
AgentAction.model_validate_json(json_text)
action.model_dump()
action.model_dump_json()
AgentAction.model_json_schema()
```

在写项目时，建议先确认你安装的 Pydantic 版本，然后统一使用一种写法。

---

## 8. 字段类型

### 定义

字段类型是指每个字段应该是什么 Python 类型。

示例：

```python
class AgentAction(BaseModel):
    intent: str
    arguments: dict[str, object]
    confidence: float
    need_tool: bool
```

### 作用

字段类型帮助你约束数据：

- `intent` 必须是字符串。
- `arguments` 必须是字典。
- `confidence` 必须是数字。
- `need_tool` 必须是布尔值。

### 注意点

LLM 输出的数据经常不稳定。例如：

```json
{
  "intent": "calculator",
  "arguments": "19 * 23 + 7",
  "confidence": "high",
  "need_tool": "yes"
}
```

这对人类也许能理解，但对程序不可靠。Pydantic 会帮助你发现这些问题。

---

## 9. 字段约束

### 定义

字段约束是在类型之外增加更具体的限制。例如：

- 字符串不能为空。
- 数字必须在 0 到 1 之间。
- intent 只能是几个允许值之一。
- 字典必须包含某些参数。

### 示例

```python
from typing import Literal
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    intent: Literal["chat", "calculator", "file_search", "todo_add"]
    arguments: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)
    need_tool: bool
```

### 作用

字段约束可以把“模型大概输出对了”进一步变成“程序确认输出可用”。

例如：

- `confidence = 1.2` 会失败。
- `intent = "unknown_tool"` 会失败。
- `arguments` 缺失时可以给默认空字典。

### 工程注意点

约束不是越严越好。太宽会让错误溜进系统，太严会导致模型稍微偏一点就失败。

早期建议这样设计：

- 关键决策字段要严格，例如 `need_tool`、`intent`。
- 可扩展字段可以稍宽，例如 `arguments`。
- 数值范围要明确，例如 `confidence` 在 0 到 1 之间。

---

## 10. 输出解析

### 定义

输出解析是把模型返回的原始文本转换成程序可用对象的过程。

完整过程通常是：

```text
模型原始输出 string
-> 提取 JSON 文本
-> json.loads 解析成 dict
-> Pydantic 校验成 BaseModel 对象
```

### 示例

```python
import json
from pydantic import ValidationError


def parse_action(raw_text: str) -> AgentAction:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"模型输出不是合法 JSON：{exc}") from exc

    try:
        return AgentAction.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"模型输出字段不符合要求：{exc}") from exc
```

### 作用

输出解析器是模型和业务逻辑之间的边界。

它的职责是：

- 接收不可靠的模型文本。
- 尽量解析成结构化数据。
- 拒绝不合法结果。
- 给出清晰错误。
- 为重试逻辑提供错误原因。

---

## 11. JSON 解析失败

### 定义

JSON 解析失败是指模型输出的文本无法被 JSON parser 解析。

例如：

```text
用户想要计算，所以结果是：
{
  "intent": "calculator",
  "arguments": {"expression": "19 * 23 + 7"},
  "confidence": 0.95,
  "need_tool": true
}
```

上面这段对人类清楚，但不是纯 JSON，因为前面有解释文字。

### 常见原因

- JSON 前后带自然语言说明。
- 使用了单引号。
- 布尔值写成 `True` / `False`。
- 多了尾随逗号。
- 缺少右括号。
- 输出了 Markdown 代码块。

例如：

```text
```json
{
  "intent": "calculator"
}
```
```

这也不是纯 JSON，需要先去掉代码块标记。

### 处理方式

早期建议采用严格策略：

```text
只接受纯 JSON。
如果解析失败，返回清晰错误并触发重试。
```

不要一开始就写很复杂的正则去“猜模型想表达什么”。解析器太宽松，会让坏数据悄悄进入系统。

---

## 12. 字段缺失

### 定义

字段缺失是指 JSON 本身合法，但缺少 Pydantic model 要求的字段。

例如：

```json
{
  "intent": "calculator",
  "arguments": {
    "expression": "19 * 23 + 7"
  },
  "need_tool": true
}
```

这里缺少 `confidence`。

### 影响

字段缺失会导致后续逻辑不确定：

- 没有 `intent`，不知道要做什么。
- 没有 `arguments`，不知道工具参数。
- 没有 `need_tool`，不知道是否调用工具。
- 没有 `confidence`，无法判断模型有多确定。

### 处理方式

有些字段应该必填，有些字段可以设置默认值。

例如：

```python
arguments: dict[str, object] = Field(default_factory=dict)
```

但对于关键字段，建议保持必填。

---

## 13. 类型错误

### 定义

类型错误是指字段存在，但类型不符合要求。

例如：

```json
{
  "intent": "calculator",
  "arguments": "19 * 23 + 7",
  "confidence": "very high",
  "need_tool": "yes"
}
```

### 影响

类型错误会污染后续代码：

- `arguments` 如果是字符串，工具层无法按参数名读取。
- `confidence` 如果是 `"very high"`，不能做数值比较。
- `need_tool` 如果是 `"yes"`，逻辑判断可能产生歧义。

### 处理方式

Pydantic 可以拦截类型错误。  
在需要更严格时，可以使用更具体的类型和约束。

例如：

```python
confidence: float = Field(ge=0, le=1)
need_tool: bool
```

如果你希望布尔值必须是真正的 `true` / `false`，而不是接受字符串转换，后续可以学习 Pydantic 的严格类型。

---

## 14. 校验失败重试

### 定义

校验失败重试是指模型第一次输出不合法时，把错误原因反馈给模型，让它重新生成符合要求的输出。

流程：

```text
调用模型
-> 得到输出
-> 解析 JSON
-> Pydantic 校验
-> 失败
-> 把错误消息和原始输出反馈给模型
-> 要求重新输出纯 JSON
-> 再次解析校验
```

### 为什么需要重试

LLM 输出不是确定性的，即使 prompt 写得很清楚，也可能偶尔失败。

重试可以提升系统鲁棒性：

- 第一次输出带了说明文字。
- 字段名写错。
- 少了字段。
- 类型不符合。

很多情况下，把具体错误反馈给模型，它能在第二次修正。

### 重试次数

子模块 2 只要求增加一次重试逻辑。

原因是：

- 一次重试足够练习失败恢复。
- 无限重试会浪费 token。
- 重试也可能持续失败。
- 后续 agent loop 还会有最大轮数控制。

建议：

```python
max_retries = 1
```

---

## 15. 错误消息设计

### 定义

错误消息设计是指当解析或校验失败时，给出人和模型都能理解的错误说明。

坏错误消息：

```text
invalid output
```

好错误消息：

```text
模型输出不是合法 JSON：第 1 行第 3 列缺少双引号。
请只输出一个 JSON 对象，不要包含 Markdown 代码块或解释文字。
```

### 作用

清晰错误消息有两个用途：

1. 给开发者调试。
2. 给模型重试时参考。

### 错误消息应该包含什么

建议包含：

- 错误类型：JSON 解析失败、字段缺失、类型错误、范围错误。
- 出错字段：例如 `confidence`。
- 期望值：例如 `0 到 1 之间的数字`。
- 实际值：例如 `"high"`。
- 修复要求：例如 `只输出纯 JSON`。

### 给模型的重试提示

示例：

```text
你上一次输出不符合要求。

错误原因：
confidence 字段必须是 0 到 1 之间的数字，但你输出了 "high"。

请重新输出一个纯 JSON 对象。
不要添加 Markdown 代码块。
不要添加解释文字。
必须包含字段：intent、arguments、confidence、need_tool。
```

---

## 16. AgentAction 示例模型

子模块 2 的练习可以先定义一个 `AgentAction`：

```python
from typing import Literal
from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    intent: Literal["chat", "calculator", "file_search", "web_summary", "todo"]
    arguments: dict[str, object] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)
    need_tool: bool
```

### 字段解释

`intent`：用户意图。  
例如普通聊天、计算、文件搜索、网页摘要、待办事项。

`arguments`：执行意图需要的参数。  
例如计算器需要 `expression`，文件搜索需要 `query` 和 `directory`。

`confidence`：模型对自己判断的置信度。  
建议范围是 0 到 1。

`need_tool`：是否需要调用工具。  
如果只是普通解释概念，通常是 `false`；如果需要计算、搜索、管理待办，通常是 `true`。

### 示例输出

普通聊天：

```json
{
  "intent": "chat",
  "arguments": {},
  "confidence": 0.82,
  "need_tool": false
}
```

计算器：

```json
{
  "intent": "calculator",
  "arguments": {
    "expression": "19 * 23 + 7"
  },
  "confidence": 0.97,
  "need_tool": true
}
```

文件搜索：

```json
{
  "intent": "file_search",
  "arguments": {
    "query": "RAG evaluation",
    "directory": "notes"
  },
  "confidence": 0.88,
  "need_tool": true
}
```

---

## 17. Prompt 如何配合结构化输出

### 不够好的 prompt

```text
请分析用户意图，并尽量输出 JSON。
```

问题是“尽量”太软，字段也不明确。

### 更好的 prompt

```text
你是一个任务解析器。
请把用户输入解析成一个 JSON 对象。

要求：
1. 只输出 JSON，不要输出 Markdown 代码块。
2. 不要添加解释文字。
3. 必须包含字段：intent、arguments、confidence、need_tool。
4. confidence 必须是 0 到 1 之间的数字。
5. need_tool 必须是 true 或 false。

允许的 intent：
- chat
- calculator
- file_search
- web_summary
- todo

用户输入：
{user_input}
```

### 注意点

prompt 可以提高成功率，但不能替代校验。

正确工程姿势是：

```text
prompt 约束输出
+ Pydantic 校验结果
+ 失败后重试或报错
```

---

## 18. 单元测试

### 为什么要测试输出解析

模型输出不稳定，所以解析器必须可靠。  
你不应该每次都调用真实模型来测试解析逻辑，因为：

- 成本高。
- 速度慢。
- 结果不稳定。
- CI 中不一定有 API key。

更好的方式是构造固定样例：

```python
def test_parse_valid_action():
    raw = """
    {
      "intent": "calculator",
      "arguments": {"expression": "1 + 2"},
      "confidence": 0.9,
      "need_tool": true
    }
    """
    action = parse_action(raw)
    assert action.intent == "calculator"
```

### 至少测试 5 类情况

建议先写这 5 个：

1. 合法 JSON，能解析成功。
2. 非法 JSON，能报出 JSON 解析错误。
3. 缺少字段，例如缺少 `confidence`。
4. 类型错误，例如 `confidence` 是 `"high"`。
5. 范围错误，例如 `confidence` 是 `1.5`。

还可以扩展：

- 多余字段。
- intent 不在允许范围内。
- arguments 不是对象。
- 模型输出 Markdown 代码块。
- 模型输出前后带解释文字。

---

## 19. 本节常见误区

### 误区 1：模型输出 JSON 就等于结构化输出

不一定。  
只有通过解析和校验后的 JSON，才算真正进入工程系统的结构化数据。

### 误区 2：只靠 prompt 就能保证格式

不可靠。  
prompt 是软约束，Pydantic 是硬校验。

### 误区 3：解析器越宽松越好

不一定。  
解析器太宽松会掩盖模型错误，让坏数据进入系统。早期建议严格一些。

### 误区 4：所有字段都应该设置默认值

不一定。  
关键字段应该必填，否则系统可能在错误数据上继续运行。

### 误区 5：重试越多越稳

不一定。  
重试会增加成本和延迟。子模块 2 阶段先做一次重试即可。

---

## 20. 复习小抄

| 概念 | 一句话理解 | 工程作用 |
| --- | --- | --- |
| Structured Output | 让模型输出固定结构的数据 | 让程序稳定读取结果 |
| 普通文本输出 | 自然语言回答 | 适合人读，不适合程序直接处理 |
| JSON | 常用结构化数据格式 | 连接模型输出和 Python 数据 |
| JSON Schema | 描述 JSON 结构的规则 | 说明字段、类型和约束 |
| Pydantic | Python 数据校验工具 | 把不可靠输入变成可靠对象 |
| BaseModel | Pydantic 模型基类 | 定义字段和校验规则 |
| 字段约束 | 类型之外的限制 | 限制范围、枚举、默认值 |
| 输出解析 | 原始文本转结构化对象 | 模型和业务逻辑之间的边界 |
| JSON 解析失败 | 文本不是合法 JSON | 需要报错或重试 |
| 字段缺失 | JSON 少了必填字段 | 防止后续逻辑缺信息 |
| 类型错误 | 字段类型不符合要求 | 防止错误数据进入系统 |
| 校验失败重试 | 把错误反馈给模型重生成 | 提高结构化输出成功率 |
| 错误消息设计 | 清晰描述失败原因 | 帮开发者调试，也帮模型修正 |
| 单元测试 | 用固定样例测试解析器 | 不依赖真实模型，稳定验证边界 |

---

## 21. 学完后的自检问题

1. 结构化输出和普通文本输出有什么区别？
2. 为什么模型输出“看起来像 JSON”还不够？
3. JSON 解析失败和 Pydantic 校验失败有什么区别？
4. `BaseModel` 在输出解析中承担什么职责？
5. `confidence` 为什么应该限制在 0 到 1 之间？
6. `need_tool` 为什么应该是布尔值，而不是字符串 `"yes"`？
7. 字段缺失时应该直接补默认值，还是报错？如何判断？
8. 为什么 agent 工程中不应该相信未经校验的模型输出？
9. 校验失败后，把什么信息反馈给模型最有帮助？
10. 如何在不调用真实模型的情况下测试输出解析器？

---

## 22. 下一步实践

下一步可以开始实现子模块 2 的小练习：

```text
1. 定义 AgentAction Pydantic model：
   - intent
   - arguments
   - confidence
   - need_tool

2. 写一个 parse_action(raw_text: str) 函数：
   - 解析 JSON
   - 使用 Pydantic 校验
   - 失败时给出清晰错误

3. 构造 5 个错误输出样例：
   - 非法 JSON
   - 缺少字段
   - 类型错误
   - confidence 超出范围
   - intent 不在允许范围内

4. 写单元测试：
   - 测合法输出
   - 测每种错误输出

5. 增加一次重试逻辑：
   - 第一次解析失败
   - 把错误原因反馈给模型
   - 要求模型重新输出纯 JSON
```

完成这部分后，你就能把子模块 1 的普通聊天调用升级成“模型输出可被程序稳定消费”的工程组件。
