from typing import Any
from dataclasses import dataclass

from pydantic import BaseModel, Field


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
    direct_answer: str | None = None


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class AgentResult(BaseModel):
    answer: str
    used_tools: list[str] = Field(default_factory=list)
    trace_id: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)


class AgentEvent(BaseModel):
    event: str
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)
