# 子模块 4 练习：手写最小 Agent Loop

这个目录不是单脚本练习，而是一个小型工程结构。原因是 agent loop 会同时涉及：

- 子模块 1：messages、system prompt、assistant/tool 消息。
- 子模块 2：结构化输出、Pydantic 校验、解析失败处理。
- 子模块 3：工具注册表、参数校验、统一 `ToolResult`。
- 子模块 4：循环控制、最大轮数、工具调用、最终回答、结构化日志。

## 文件说明

```text
exercise/submodule_4_exercise/
  README.md          练习说明
  __init__.py
  actions.py         模型决策结构和解析器
  prompts.py         agent prompt 和 messages 构造
  mock_llm.py        模拟 LLM，避免真实 API 调用
  loop.py            最小 agent loop 主体
  demo.py            命令行演示和自检入口
```

## 建议完成顺序

1. 阅读 `actions.py`，完成模型决策结构解析。
2. 阅读 `prompts.py`，理解 agent prompt 如何告诉模型可用工具。
3. 阅读 `mock_llm.py`，理解如何不用真实模型测试 agent loop。
4. 完成 `loop.py` 中的 TODO，这是本练习核心。
5. 运行 `demo.py` 的不同脚本，观察单工具、多工具、解析失败、最大轮数等场景。

## 运行方式

请在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m exercise.submodule_4_exercise.demo --list-scripts
.\.venv\Scripts\python.exe -m exercise.submodule_4_exercise.demo --demo calculator
.\.venv\Scripts\python.exe -m exercise.submodule_4_exercise.demo --demo todo_two_steps
.\.venv\Scripts\python.exe -m exercise.submodule_4_exercise.demo --self-check
```

刚生成时，部分入口会提示 TODO 未完成，这是正常的。你的目标是让 `--self-check` 最终通过。

## 本练习不做什么

- 不调用真实 LLM。
- 不接 LangChain 或 LangGraph。
- 不做长期记忆。
- 不做多 agent。
- 不做复杂规划器。

本阶段只练一个核心能力：**模型输出结构化决策，程序用确定性代码控制循环和工具执行。**

