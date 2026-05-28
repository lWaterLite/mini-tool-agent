import re
import logging
from time import perf_counter
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi import status

from app.agent.models import AgentEvent, AgentResult, ToolCallRecord
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger, log_event, summarize_text
from app.tools.registry import ToolRegistry


logger = get_logger(__name__)


@dataclass(frozen=True)
class PlannedToolCall:
    """Agent 规划出的单个工具步骤。"""

    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentPlan:
    """Agent 对本次请求的计划。"""

    tool_calls: list[PlannedToolCall]
    clarification: str | None = None


class AgentService:
    """最小 Agent 服务。

    这个类故意不依赖 FastAPI，因此它可以被 API、测试、CLI 或其他服务复用。
    当前的“模型”是规则型 mock planner，目的是把服务化工程结构先练扎实。
    """

    def __init__(self, tool_registry: ToolRegistry, settings: Settings) -> None:
        self._tools = tool_registry
        self._settings = settings

    async def run(
        self,
        message: str,
        trace_id: str,
        session_id: str | None = None,
        max_steps: int | None = None,
    ) -> AgentResult:
        """一次性执行 Agent，并返回最终结果。"""
        events: list[AgentEvent] = []
        async for event in self.stream(
            message=message,
            trace_id=trace_id,
            session_id=session_id,
            max_steps=max_steps,
        ):
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
        max_steps: int | None = None,
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

        resolved_max_steps = self._resolve_max_steps(max_steps)
        log_event(
            logger,
            logging.INFO,
            "request_started",
            trace_id=trace_id,
            session_id=session_id,
            message_preview=summarize_text(cleaned_message),
            message_length=len(cleaned_message),
            max_steps=resolved_max_steps,
        )
        yield AgentEvent(
            event="start",
            trace_id=trace_id,
            data={"message": cleaned_message, "session_id": session_id, "max_steps": resolved_max_steps},
        )

        plan = self._plan(cleaned_message, session_id=session_id)
        log_event(
            logger,
            logging.INFO,
            "agent_plan_created",
            trace_id=trace_id,
            planned_tools=[call.name for call in plan.tool_calls],
            clarification=plan.clarification is not None,
        )
        if plan.clarification is not None:
            log_event(
                logger,
                logging.INFO,
                "request_finished",
                trace_id=trace_id,
                final_status="clarification",
                used_tools=[],
            )
            yield AgentEvent(
                event="final",
                trace_id=trace_id,
                data={"answer": plan.clarification, "used_tools": []},
            )
            return

        if not plan.tool_calls:
            answer = "我已经收到你的消息。当前练习版 Agent 可以处理计算、文件搜索、网页摘要和待办事项。"
            log_event(
                logger,
                logging.INFO,
                "request_finished",
                trace_id=trace_id,
                final_status="direct_answer",
                used_tools=[],
            )
            yield AgentEvent(
                event="final",
                trace_id=trace_id,
                data={"answer": answer, "used_tools": []},
            )
            return

        if len(plan.tool_calls) > resolved_max_steps:
            log_event(
                logger,
                logging.WARNING,
                "request_rejected",
                trace_id=trace_id,
                reason="max_steps_exceeded",
                planned_steps=len(plan.tool_calls),
                max_steps=resolved_max_steps,
            )
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                f"本次请求计划执行 {len(plan.tool_calls)} 个工具步骤，超过 max_steps={resolved_max_steps}",
                trace_id=trace_id,
            )

        records: list[ToolCallRecord] = []
        for index, planned_call in enumerate(plan.tool_calls, start=1):
            log_event(
                logger,
                logging.INFO,
                "tool_call_started",
                trace_id=trace_id,
                step=index,
                tool_name=planned_call.name,
                tool_arguments=planned_call.arguments,
            )
            yield AgentEvent(
                event="tool_call",
                trace_id=trace_id,
                data={"step": index, "name": planned_call.name, "arguments": planned_call.arguments},
            )

            tool = self._tools.get(planned_call.name)
            started_at = perf_counter()
            try:
                result = await tool.arun(planned_call.arguments, trace_id=trace_id)
            except AppError as exc:
                log_event(
                    logger,
                    logging.ERROR,
                    "tool_call_failed",
                    trace_id=trace_id,
                    step=index,
                    tool_name=planned_call.name,
                    latency_ms=round((perf_counter() - started_at) * 1000, 2),
                    error_code=exc.code,
                    error_message=exc.message,
                )

                log_event(
                    logger,
                    logging.INFO,
                    "request_finished",
                    trace_id=trace_id,
                    final_status="error",
                    error_code=exc.code,
                    used_tools=[record.name for record in records] + [planned_call.name],
                )
                raise
            except Exception:
                log_event(
                    logger,
                    logging.ERROR,
                    "tool_call_failed",
                    trace_id=trace_id,
                    step=index,
                    tool_name=planned_call.name,
                    latency_ms=round((perf_counter() - started_at) * 1000, 2),
                    error_code=ErrorCode.INTERNAL_ERROR,
                    error_message="未处理工具异常",
                )

                log_event(
                    logger,
                    logging.INFO,
                    "request_finished",
                    trace_id=trace_id,
                    final_status="error",
                    error_code=ErrorCode.INTERNAL_ERROR,
                    used_tools=[record.name for record in records] + [planned_call.name],
                )
                raise

            log_event(
                logger,
                logging.INFO,
                "tool_call_finished",
                trace_id=trace_id,
                step=index,
                tool_name=planned_call.name,
                latency_ms=round((perf_counter() - started_at) * 1000, 2),
                status="success",
            )
            record = ToolCallRecord(
                name=planned_call.name,
                arguments=planned_call.arguments,
                result=result.model_dump(),
            )
            records.append(record)

            yield AgentEvent(
                event="tool_result",
                trace_id=trace_id,
                data=record.model_dump(),
            )

        log_event(
            logger,
            logging.INFO,
            "request_finished",
            trace_id=trace_id,
            final_status="success",
            used_tools=[record.name for record in records],
        )
        yield AgentEvent(
            event="final",
            trace_id=trace_id,
            data={
                "answer": self._build_final_answer(records),
                "used_tools": [record.name for record in records],
            },
        )

    def _resolve_max_steps(self, max_steps: int | None) -> int:
        if max_steps is not None:
            return max_steps
        return self._settings.max_agent_steps

    def _plan(self, message: str, session_id: str | None) -> AgentPlan:
        """根据用户输入选择工具。

        这是规则型 planner，不追求像真实 LLM 那样理解所有自然语言。
        它的价值是让你能清楚看到“规划 -> 执行工具 -> 汇总回答”的工程边界。
        """
        tool_calls: list[PlannedToolCall] = []

        expression = self._extract_expression(message)
        if expression:
            tool_calls.append(PlannedToolCall("calculator", {"expression": expression}))

        file_query = self._extract_file_query(message)
        if file_query == "":
            return AgentPlan(
                tool_calls=[],
                clarification="你想搜索文件，但没有说明关键词。请告诉我要搜索什么内容。",
            )
        if file_query is not None:
            tool_calls.append(
                PlannedToolCall(
                    "file_search",
                    {"query": file_query, "max_results": self._settings.max_file_search_results},
                )
            )

        url = self._extract_url(message)
        if url is not None:
            tool_calls.append(PlannedToolCall("web_summary_mock", {"url": url}))

        tool_calls.extend(self._extract_todo_calls(message, session_id=session_id))

        return AgentPlan(tool_calls=tool_calls)

    def _extract_expression(self, message: str) -> str | None:
        if "计算" not in message and not re.search(r"\d+\s*[\+\-\*/\^]", message):
            return None

        candidate = message.replace("帮我", "").replace("请", "").replace("计算", "").strip()
        candidate = candidate.replace("等于多少", "").replace("是多少", "").strip()
        candidate = candidate.replace("^", "**")
        match = re.search(r"[0-9\.\+\-\*/\*\(\)\s]+", candidate)
        if match is None:
            return None
        expression = match.group(0).strip()
        if expression and re.fullmatch(r"[0-9\.\+\-\*/\*\(\)\s]+", expression):
            return expression
        return None

    def _extract_file_query(self, message: str) -> str | None:
        search_markers = ("搜索文件", "查找文件", "搜索文档", "查找文档", "文件里找", "文档里找")
        if not any(marker in message for marker in search_markers):
            return None

        query = message
        for marker in search_markers:
            query = query.replace(marker, " ")
        query = re.sub(r"(帮我|请|一下|关于|包含|关键词|并总结|总结)", " ", query)
        query = re.sub(r"https?://\S+", " ", query)
        query = re.sub(r"\s+", " ", query).strip(" ，。,.")
        return query

    def _extract_url(self, message: str) -> str | None:
        match = re.search(r"https?://\S+", message)
        if match is None:
            return None
        return match.group(0).rstrip("，。,.")

    def _extract_todo_calls(self, message: str, session_id: str | None) -> list[PlannedToolCall]:
        calls: list[PlannedToolCall] = []
        normalized_session_id = session_id or "default"

        if "添加待办" in message:
            content = message.split("添加待办", 1)[1]
            content = re.split(r"(然后|并且|并查看|查看待办|待办列表)", content, maxsplit=1)[0].strip(" ：:，。,.")
            if not content:
                return [PlannedToolCall("todo", {"action": "list", "session_id": normalized_session_id})]
            calls.append(
                PlannedToolCall(
                    "todo",
                    {"action": "add", "content": content, "session_id": normalized_session_id},
                )
            )

        done_match = re.search(r"(完成待办|标记完成)\s*(?P<item_id>todo_[0-9a-fA-F]+)", message)
        if done_match is not None:
            calls.append(
                PlannedToolCall(
                    "todo",
                    {"action": "done", "item_id": done_match.group("item_id"), "session_id": normalized_session_id},
                )
            )

        if "查看待办" in message or "待办列表" in message:
            calls.append(PlannedToolCall("todo", {"action": "list", "session_id": normalized_session_id}))

        return calls

    def _build_final_answer(self, records: list[ToolCallRecord]) -> str:
        if len(records) == 1:
            return self._build_single_tool_answer(records[0].name, str(records[0].result["output"]))

        lines = [f"已完成 {len(records)} 个工具步骤："]
        for index, record in enumerate(records, start=1):
            output = str(record.result["output"])
            lines.append(f"{index}. {record.name}：{output}")
        return "\n".join(lines)

    def _build_single_tool_answer(self, tool_name: str, output: str) -> str:
        if tool_name == "calculator":
            return f"计算结果：{output}"
        if tool_name == "file_search":
            return f"文件搜索结果：{output}"
        if tool_name == "web_summary_mock":
            return f"网页摘要：{output}"
        if tool_name == "todo":
            return f"待办事项结果：{output}"
        return output
