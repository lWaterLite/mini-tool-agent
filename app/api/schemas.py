from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="服务状态")
    service: str = Field(description="服务名称")
    environment: str = Field(description="当前运行环境")


class ToolInfo(BaseModel):
    name: str = Field(description="工具名称")
    description: str = Field(description="工具说明")
    parameters_schema: dict[str, Any] = Field(description="工具参数 JSON Schema")


class ToolsResponse(BaseModel):
    tools: list[ToolInfo]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="用户输入消息")
    session_id: str | None = Field(default=None, max_length=80, description="可选会话 ID")

    # TODO 练习 2：
    # 添加一个 max_steps 字段，限制 Agent Loop 最多执行多少步。
    # 思考：这个限制应该放在 API 请求里、Settings 里，还是两者都支持？


class ToolCallView(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]


class ChatResponse(BaseModel):
    answer: str
    used_tools: list[str]
    trace_id: str
    tool_calls: list[ToolCallView] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    code: str
    message: str
    trace_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class StreamEvent(BaseModel):
    event: str = Field(description="事件名称，例如 start、tool_call、final、error")
    trace_id: str
    data: dict[str, Any] = Field(default_factory=dict)

