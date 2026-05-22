"""模拟 LLM。

本文件的目标是让你在不调用真实 API 的情况下测试 agent loop。
这复习了子模块 2 和子模块 4 的关键工程思想：
核心逻辑应该可以被 mock 模型稳定测试。
"""

from __future__ import annotations

from dataclasses import dataclass


class ScriptExhaustedError(RuntimeError):
    """脚本中的模拟模型输出已经用完。"""


@dataclass
class ScriptedLLM:
    """按顺序返回预设输出的模拟 LLM。"""

    outputs: list[str]
    call_count: int = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        """返回下一条模拟模型输出。

        TODO 6：
        可以先阅读，不一定要修改。
        思考：
        1. 为什么 mock LLM 对 agent loop 测试很重要？
        2. 为什么不建议在单元测试里调用真实模型？
        3. messages 参数在这里虽然没用，但为什么仍然保留？
        """

        if self.call_count >= len(self.outputs):
            raise ScriptExhaustedError("模拟 LLM 输出已用完。")

        output = self.outputs[self.call_count]
        self.call_count += 1
        return output


SCRIPTS: dict[str, list[str]] = {
    "calculator": [
        """
        {
          "type": "tool_call",
          "tool_name": "calculator",
          "arguments": {
            "expression": "19 * 23 + 7"
          },
          "reason": "用户要求精确计算。"
        }
        """.strip(),
        """
        {
          "type": "final_answer",
          "answer": "19 * 23 + 7 的计算结果是 444。"
        }
        """.strip(),
    ],
    "web_summary": [
        """
        {
          "type": "tool_call",
          "tool_name": "web_summary_mock",
          "arguments": {
            "url": "https://example.com/agent-intro"
          },
          "reason": "用户要求总结指定网页。"
        }
        """.strip(),
        """
        {
          "type": "final_answer",
          "answer": "这个网页介绍了 AI Agent 如何理解任务、调用工具并整合结果。"
        }
        """.strip(),
    ],
    "todo_two_steps": [
        """
        {
          "type": "tool_call",
          "tool_name": "todo",
          "arguments": {
            "action": "add",
            "title": "周五整理 mini-tool-agent README"
          },
          "reason": "用户要求新增一个待办事项。"
        }
        """.strip(),
        """
        {
          "type": "tool_call",
          "tool_name": "todo",
          "arguments": {
            "action": "list"
          },
          "reason": "用户还要求查看当前待办列表。"
        }
        """.strip(),
        """
        {
          "type": "final_answer",
          "answer": "已添加待办：周五整理 mini-tool-agent README，并已查看当前待办列表。"
        }
        """.strip(),
    ],
    "unknown_tool": [
        """
        {
          "type": "tool_call",
          "tool_name": "run_python_code",
          "arguments": {
            "code": "print('bad')"
          },
          "reason": "错误示例：模型试图调用未注册工具。"
        }
        """.strip(),
    ],
    "bad_json": [
        "我应该调用计算器。",
    ],
    "max_steps": [
        """
        {
          "type": "tool_call",
          "tool_name": "calculator",
          "arguments": {
            "expression": "1 + 1"
          },
          "reason": "一直调用工具，用于测试最大轮数。"
        }
        """.strip(),
        """
        {
          "type": "tool_call",
          "tool_name": "calculator",
          "arguments": {
            "expression": "2 + 2"
          },
          "reason": "继续调用工具。"
        }
        """.strip(),
        """
        {
          "type": "tool_call",
          "tool_name": "calculator",
          "arguments": {
            "expression": "3 + 3"
          },
          "reason": "继续调用工具。"
        }
        """.strip(),
    ],
}


DEFAULT_USER_INPUTS = {
    "calculator": "帮我计算 19 * 23 + 7。",
    "web_summary": "给我总结一下这个网页：https://example.com/agent-intro。",
    "todo_two_steps": "添加一个待办：周五整理 mini-tool-agent README，然后查看当前待办列表。",
    "unknown_tool": "请执行一段 Python 代码。",
    "bad_json": "帮我计算 1 + 2。",
    "max_steps": "请一直计算一些数字。",
}

