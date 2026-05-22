"""最小 Agent Loop 主体。

本文件是子模块 4 的核心练习。
它会复用：
- 子模块 2 的结构化解析思路
- 子模块 3 的工具注册表与 ToolResult
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from exercise.submodule_3_exercise import ToolRegistry, build_default_registry
from exercise.submodule_4_exercise.actions import (
    ActionParseError,
    AgentAction,
    action_to_assistant_message,
    parse_agent_action,
)
from exercise.submodule_4_exercise.prompts import (
    build_initial_messages,
    build_system_prompt,
    build_tool_message,
)


class LLMClient(Protocol):
    """最小 LLM 客户端协议。"""

    def complete(self, messages: list[dict[str, str]]) -> str:
        """根据 messages 返回模型原始输出。"""


@dataclass
class AgentRunResult:
    """agent 执行结果。"""

    ok: bool
    final_answer: str
    trace_id: str
    steps: list[dict[str, Any]]
    messages: list[dict[str, str]]
    error: str | None = None


@dataclass
class MiniAgent:
    """最小 tool agent。"""

    llm: LLMClient
    registry: ToolRegistry = field(default_factory=build_default_registry)
    max_steps: int = 5

    def run(self, user_input: str) -> AgentRunResult:
        """运行 agent loop。

        TODO 7：
        完成最小 agent loop。

        建议流程：
        1. 生成 trace_id。
        2. 使用 registry.list_tools() 构造 system prompt。
        3. 使用 build_initial_messages(system_prompt, user_input) 构造 messages。
        4. 初始化 steps 日志列表。
        5. for step in range(1, max_steps + 1):
           5.1 调用 self.llm.complete(messages)，得到 raw_output。
           5.2 解析 raw_output -> AgentAction。
           5.3 把 action 作为 assistant message 追加进 messages。
           5.4 如果 action.type == "final_answer"，返回成功结果。
           5.5 如果 action.type == "tool_call"，调用 self.execute_tool(action)。
           5.6 把工具结果作为 tool message 追加进 messages。
           5.7 记录结构化 step 日志。
        6. 超过 max_steps 后返回失败结果。

        必须处理：
        - 模型输出解析失败。
        - 工具不存在。
        - 工具参数错误。
        - 工具执行失败。
        - 超过最大轮数。

        思考题：
        - action_to_assistant_message 应该在工具执行前还是后追加？
        - 工具失败后应该继续循环，还是直接返回失败？
        - max_steps 统计的是模型决策次数，还是工具调用次数？
        """

        raise NotImplementedError("TODO 7：请实现 MiniAgent.run。")

    def execute_tool(self, action: AgentAction) -> tuple[dict[str, Any], str]:
        """执行工具并返回 step 日志和工具消息内容。

        TODO 8：
        完成工具执行：
        1. 确认 action.type 是 tool_call。
        2. 确认 action.tool_name 不为空。
        3. 记录开始时间。
        4. 调用 self.registry.run(action.tool_name, action.arguments)。
        5. 记录 latency_ms。
        6. 生成 step_log，包含 event、tool_name、arguments、ok、error、latency_ms。
        7. 把 ToolResult 转成 JSON 字符串，作为 tool message content。

        思考题：
        - 为什么 execute_tool 不应该直接 raise 工具错误？
        - 日志里是否应该记录完整 arguments？什么时候需要脱敏？
        """

        raise NotImplementedError("TODO 8：请实现 MiniAgent.execute_tool。")

    def _fail(
        self,
        trace_id: str,
        messages: list[dict[str, str]],
        steps: list[dict[str, Any]],
        error: str,
    ) -> AgentRunResult:
        """构造失败结果。"""

        return AgentRunResult(
            ok=False,
            final_answer="",
            trace_id=trace_id,
            steps=steps,
            messages=messages,
            error=error,
        )


def make_step_log(
    step: int,
    event: str,
    **extra: Any,
) -> dict[str, Any]:
    """构造结构化 step 日志。

    TODO 9：
    你可以直接使用这个函数，也可以扩展它。
    建议至少包含：
    - step
    - event
    - 额外字段
    """

    return {"step": step, "event": event, **extra}


def new_trace_id() -> str:
    """生成 trace id。"""

    return uuid.uuid4().hex[:12]

