import re
from collections.abc import AsyncIterator
from typing import Any

from fastapi import status

from app.agent.models import AgentEvent, AgentResult, ToolCallRecord
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.tools.registry import ToolRegistry


class AgentService:
    """最小 Agent 服务。

    这个类故意不依赖 FastAPI，因此它可以被 API、测试、CLI 或其他服务复用。
    当前的“模型”是规则型 mock planner，目的是把服务化工程结构先练扎实。
    """

    def __init__(self, tool_registry: ToolRegistry, settings: Settings) -> None:
        self._tools = tool_registry
        self._settings = settings

    async def run(self, message: str, trace_id: str, session_id: str | None = None) -> AgentResult:
        """一次性执行 Agent，并返回最终结果。"""
        events: list[AgentEvent] = []
        async for event in self.stream(message=message, trace_id=trace_id, session_id=session_id):
            events.append(event)

        final_events = [event for event in events if event.event == "final"]
        if not final_events:
            raise AppError(
                ErrorCode.AGENT_ERROR,
                "Agent 没有生成最终回答",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                trace_id=trace_id,
            )

        final_data = final_events[-1].data
        tool_calls = [
            ToolCallRecord(**event.data)
            for event in events
            if event.event == "tool_result"
        ]

        return AgentResult(
            answer=str(final_data["answer"]),
            used_tools=list(final_data.get("used_tools", [])),
            trace_id=trace_id,
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        message: str,
        trace_id: str,
        session_id: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """流式执行 Agent。

        这里用 async generator 演示 streaming 的核心形式：
        - API 层可以把每个 AgentEvent 转成 SSE。
        - 测试层可以直接消费事件。
        - Agent 层不需要知道 HTTP 的存在。
        """
        cleaned_message = message.strip()
        if not cleaned_message:
            raise AppError(ErrorCode.INVALID_REQUEST, "用户消息不能为空", trace_id=trace_id)

        yield AgentEvent(
            event="start",
            trace_id=trace_id,
            data={"message": cleaned_message, "session_id": session_id},
        )

        plan = self._plan(cleaned_message)
        if plan is None:
            answer = "我已经收到你的消息。当前练习版 Agent 可以处理计算、文件搜索、网页摘要和待办事项。"
            yield AgentEvent(
                event="final",
                trace_id=trace_id,
                data={"answer": answer, "used_tools": []},
            )
            return

        tool_name, arguments = plan
        yield AgentEvent(
            event="tool_call",
            trace_id=trace_id,
            data={"name": tool_name, "arguments": arguments},
        )

        tool = self._tools.get(tool_name)
        result = await tool.arun(arguments, trace_id=trace_id)

        yield AgentEvent(
            event="tool_result",
            trace_id=trace_id,
            data={
                "name": tool_name,
                "arguments": arguments,
                "result": result.model_dump(),
            },
        )

        yield AgentEvent(
            event="final",
            trace_id=trace_id,
            data={
                "answer": self._build_answer(tool_name, result.output),
                "used_tools": [tool_name],
            },
        )

    def _plan(self, message: str) -> tuple[str, dict[str, Any]] | None:
        """根据用户输入选择工具。

        TODO 练习 5：
        当前 planner 是规则型实现。请尝试新增：
        - 更稳健的文件搜索意图识别。
        - 多工具组合，例如先搜索文件再总结。
        - 当意图不明确时返回澄清问题，而不是直接猜工具。
        """
        expression = self._extract_expression(message)
        if expression:
            return "calculator", {"expression": expression}

        if message.startswith("搜索文件") or message.startswith("查找文件"):
            query = message.replace("搜索文件", "", 1).replace("查找文件", "", 1).strip()
            return "file_search", {"query": query or message, "max_results": self._settings.max_file_search_results}

        if "http://" in message or "https://" in message:
            url = self._extract_url(message)
            return "web_summary_mock", {"url": url}

        if message.startswith("添加待办"):
            content = message.replace("添加待办", "", 1).strip()
            return "todo", {"action": "add", "content": content}

        if "查看待办" in message or "待办列表" in message:
            return "todo", {"action": "list"}

        return None

    def _extract_expression(self, message: str) -> str | None:
        if "计算" not in message and not re.search(r"\d+\s*[\+\-\*/]", message):
            return None

        candidate = message.replace("帮我", "").replace("请", "").replace("计算", "").strip()
        candidate = candidate.replace("等于多少", "").replace("是多少", "").strip()
        if re.fullmatch(r"[0-9\.\+\-\*/\(\)\s]+", candidate):
            return candidate
        return None

    def _extract_url(self, message: str) -> str:
        match = re.search(r"https?://\S+", message)
        if match is None:
            raise AppError(ErrorCode.INVALID_REQUEST, "没有找到 URL")
        return match.group(0)

    def _build_answer(self, tool_name: str, output: str) -> str:
        if tool_name == "calculator":
            return f"计算结果：{output}"
        if tool_name == "file_search":
            return f"文件搜索结果：{output}"
        if tool_name == "web_summary_mock":
            return f"网页摘要：{output}"
        if tool_name == "todo":
            return f"待办事项结果：{output}"
        return output

