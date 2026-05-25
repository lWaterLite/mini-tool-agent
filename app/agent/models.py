from typing import Any

from pydantic import BaseModel, Field


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

