"""模型决策结构与解析器。

本文件复习子模块 2：
- 结构化输出
- Pydantic BaseModel
- Literal 约束
- JSON 解析失败
- 字段校验失败
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class ActionParseError(ValueError):
    """模型决策解析失败。"""


class ToolCallAction(BaseModel):
    """模型请求调用工具。"""

    type: Literal["tool_call"]
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", description="模型选择该工具的简短原因")


class FinalAnswerAction(BaseModel):
    """模型给出最终回答。"""

    type: Literal["final_answer"]
    answer: str = Field(min_length=1)


class AgentAction(BaseModel):
    """统一模型决策结构。

    为了降低初学难度，这里不用 Pydantic 的 discriminated union，
    而是用一个外层模型承载两种 action。

    TODO 1：
    完成跨字段校验：
    1. 当 type == "tool_call" 时，tool_name 必须存在。
    2. 当 type == "tool_call" 时，arguments 必须是 dict。
    3. 当 type == "final_answer" 时，answer 必须存在且非空。
    4. 当 type == "final_answer" 时，可以忽略 tool_name 和 arguments。

    思考题：
    - 为什么这里需要跨字段校验？
    - 如果模型同时输出 tool_name 和 answer，应该如何处理？
    """

    type: Literal["tool_call", "final_answer"]
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    answer: str | None = None
    reason: str = ""

    @model_validator(mode="after")
    def validate_by_type(self) -> AgentAction:
        if self.type == "tool_call":
            if not self.tool_name:
                raise ValueError("当 type 为 tool_call 时，tool_name 不能为空。")
            if not isinstance(self.arguments, dict):
                raise ValueError("当 type 为 tool_call 时，arguments 的类型必须为 dict。")
        if self.type == "final_answer":
            if not self.answer:
                raise ValueError("当 type 为 final_answer 时，answer 不能为空。")

        return self


def parse_agent_action(raw_text: str) -> AgentAction:
    """把模型原始输出解析成 AgentAction。

    TODO 2：
    完成解析器：
    1. 使用 json.loads(raw_text) 解析 JSON。
    2. JSON 解析失败时抛出 ActionParseError。
    3. 使用 AgentAction.model_validate(data) 做字段校验。
    4. Pydantic 校验失败时抛出 ActionParseError。
    5. 成功时返回 AgentAction。

    思考题：
    - 为什么 agent loop 不能直接相信模型输出？
    - 解析失败时应该重试、终止，还是把错误加入 messages？
    """

    try:
        action_json = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ActionParseError(f"模型输出不是合法 JSON：{e}") from e

    try:
        agent_action = AgentAction.model_validate(action_json)
    except ValidationError as e:
        raise ActionParseError(f"模型决策字段校验失败: {e}") from e

    return agent_action


def action_to_assistant_message(action: AgentAction) -> dict[str, str]:
    """把结构化 action 转成 assistant message。

    TODO 3：
    实现这个函数，用于把模型决策追加回 messages。

    提示：
    - role 固定为 "assistant"。
    - content 可以使用 action.model_dump_json()。
    """

    return {
        "role": "assistant",
        "content": action.model_dump_json(),
    }


VALID_TOOL_CALL = """
{
  "type": "tool_call",
  "tool_name": "calculator",
  "arguments": {
    "expression": "19 * 23 + 7"
  },
  "reason": "用户要求精确计算。"
}
""".strip()

VALID_FINAL_ANSWER = """
{
  "type": "final_answer",
  "answer": "计算结果是 444。"
}
""".strip()

INVALID_ACTION_JSON = """
我应该调用 calculator 工具。
""".strip()

INVALID_ACTION_SCHEMA = """
{
  "type": "tool_call",
  "arguments": {
    "expression": "1 + 2"
  }
}
""".strip()
