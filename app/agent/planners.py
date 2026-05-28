import json
import re
from abc import ABC, abstractmethod
from typing import Any

from fastapi import status
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.agent.models import AgentPlan, PlannedToolCall
from app.agent.prompts import build_tool_prompt
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.tools.registry import ToolRegistry


class BasePlanner(ABC):
    """规划器抽象。

    规划器只负责把用户消息转换成工具计划，不负责执行工具。
    """

    @abstractmethod
    async def plan(self, message: str, session_id: str | None) -> AgentPlan:
        """根据用户消息生成 AgentPlan。"""


class RuleBasedPlanner(BasePlanner):
    """规则型 mock planner。

    它不调用真实 LLM，适合学习、测试和无 API key 的本地运行。
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def plan(self, message: str, session_id: str | None) -> AgentPlan:
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


class LLMToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMPlanOutput(BaseModel):
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    clarification: str | None = None
    direct_answer: str | None = None


class LLMPlanner(BasePlanner):
    """真实 LLM planner。

    它使用 OpenAI 兼容 Chat Completions 接口生成结构化工具计划。
    测试时可以传入 fake client，避免调用真实模型。
    """

    def __init__(
        self,
        settings: Settings,
        tool_registry: ToolRegistry,
        client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._tool_registry = tool_registry
        self._client = client

    async def plan(self, message: str, session_id: str | None) -> AgentPlan:
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self._settings.llm_model,
                temperature=self._settings.llm_temperature,
                max_tokens=self._settings.llm_max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": self._build_user_prompt(message, session_id)},
                ],
            )
        except AppError:
            raise
        except Exception as exc:
            raise AppError(
                ErrorCode.AGENT_ERROR,
                "LLM planner 调用失败",
                status_code=status.HTTP_502_BAD_GATEWAY,
            ) from exc

        content = response.choices[0].message.content
        return self._parse_plan(content)

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._create_client(self._settings)
        return self._client

    def _create_client(self, settings: Settings) -> AsyncOpenAI:
        if not settings.llm_api_key:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                "AGENT_PLANNER_MODE=llm 时必须配置 LLM_API_KEY 或 OPENAI_API_KEY",
            )
        kwargs: dict[str, Any] = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        return AsyncOpenAI(**kwargs)

    def _build_system_prompt(self) -> str:
        return "\n".join(
            [
                "你是 mini-tool-agent 的工具规划器。",
                "你的任务是根据用户消息判断是否需要工具；需要工具时生成工具调用计划，不需要工具时生成 direct_answer。",
                "必须只输出 JSON 对象，不要输出 Markdown 或解释文字。",
                "",
                "输出格式：",
                '{"tool_calls":[{"name":"工具名称","arguments":{}}],"clarification":null,"direct_answer":null}',
                "",
                "如果不需要工具，请直接回答用户，并输出：",
                '{"tool_calls":[],"clarification":null,"direct_answer":"你的直接回答"}',
                "",
                "如果用户意图不清楚，输出：",
                '{"tool_calls":[],"clarification":"需要向用户澄清的问题","direct_answer":null}',
                "",
                build_tool_prompt(self._tool_registry),
            ]
        )

    def _build_user_prompt(self, message: str, session_id: str | None) -> str:
        session_hint = session_id or "default"
        return f"session_id: {session_hint}\n用户消息：{message}"

    def _parse_plan(self, content: str | None) -> AgentPlan:
        if not content:
            raise AppError(ErrorCode.AGENT_ERROR, "LLM planner 返回空内容")

        try:
            payload = json.loads(_extract_json_object(content))
            parsed = LLMPlanOutput.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise AppError(ErrorCode.AGENT_ERROR, "LLM planner 返回的计划格式不合法") from exc

        known_tools = {tool.name for tool in self._tool_registry.list_tools()}
        tool_calls: list[PlannedToolCall] = []
        for tool_call in parsed.tool_calls:
            if tool_call.name not in known_tools:
                raise AppError(ErrorCode.AGENT_ERROR, f"LLM planner 返回了未知工具：{tool_call.name}")
            tool_calls.append(PlannedToolCall(tool_call.name, tool_call.arguments))

        return AgentPlan(
            tool_calls=tool_calls,
            clarification=parsed.clarification,
            direct_answer=parsed.direct_answer,
        )


def build_planner(settings: Settings, tool_registry: ToolRegistry) -> BasePlanner:
    mode = settings.agent_planner_mode.lower()
    if mode == "mock":
        return RuleBasedPlanner(settings)
    if mode == "llm":
        return LLMPlanner(settings, tool_registry)
    raise ValueError(f"不支持的 AGENT_PLANNER_MODE：{settings.agent_planner_mode}")


def _extract_json_object(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        match = re.search(r"```(?:json)?\s*(?P<body>\{.*\})\s*```", stripped, flags=re.DOTALL)
        if match is not None:
            return match.group("body")
    return stripped
