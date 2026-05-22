"""Agent prompt 与 messages 构造。

本文件复习子模块 1：
- system message
- user message
- assistant message
- tool message

也复习子模块 3：
- 工具 schema
- 工具列表如何暴露给模型
"""

from __future__ import annotations

import json
from typing import Any


AGENT_SYSTEM_PROMPT_TEMPLATE = """
你是一个最小 tool agent。
你需要在每一步只输出一个 JSON 对象。

你有两种输出类型：

1. 调用工具：
{{
  "type": "tool_call",
  "tool_name": "工具名称",
  "arguments": {{}},
  "reason": "为什么需要调用这个工具"
}}

2. 最终回答：
{{
  "type": "final_answer",
  "answer": "给用户的最终回答"
}}

规则：
1. 只输出 JSON，不要输出 Markdown 代码块。
2. 不要添加解释文字。
3. 如果需要精确计算，使用 calculator。
4. 如果需要搜索本地文本文件，使用 file_search。
5. 如果需要摘要指定网页，使用 web_summary_mock。
6. 如果需要管理待办事项，使用 todo。
7. 工具返回结果后，你应该根据结果决定继续调用工具或给出 final_answer。
8. 不要调用工具列表之外的工具。

可用工具 schema：
{tools_json}
""".strip()


def build_system_prompt(tools_schema: list[dict[str, Any]]) -> str:
    """构造 system prompt。

    TODO 4：
    当前函数给了基础实现要求，请你完成：
    1. 把 tools_schema 转成格式化 JSON 字符串。
    2. 填入 AGENT_SYSTEM_PROMPT_TEMPLATE。
    3. ensure_ascii=False，方便中文正常展示。

    思考题：
    - 工具 schema 放进 prompt 的目的是什么？
    - schema 太长时会有什么问题？
    """

    raise NotImplementedError("TODO 4：请实现 build_system_prompt。")


def build_initial_messages(system_prompt: str, user_input: str) -> list[dict[str, str]]:
    """构造初始 messages。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]


def build_tool_message(tool_name: str, tool_result_json: str) -> dict[str, str]:
    """构造工具结果 message。

    TODO 5：
    完成工具消息构造：
    1. role 使用 "tool"。
    2. content 放工具结果 JSON 字符串。
    3. 为了调试方便，可以把工具名放进 name 字段。

    思考题：
    - 为什么工具结果要追加回 messages？
    - 工具结果应该给用户看，还是给模型继续观察？
    """

    raise NotImplementedError("TODO 5：请实现 build_tool_message。")


def summarize_messages(messages: list[dict[str, str]]) -> str:
    """生成便于调试的 messages 摘要。"""

    lines = []
    for index, message in enumerate(messages, start=1):
        content = message.get("content", "")
        compact = content.replace("\n", " ")
        if len(compact) > 100:
            compact = compact[:100] + "..."
        lines.append(f"{index}. {message.get('role')}: {compact}")
    return "\n".join(lines)

