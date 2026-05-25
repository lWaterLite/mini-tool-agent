import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import AppState, get_app_state
from app.api.schemas import ChatRequest, ChatResponse, HealthResponse, ToolInfo, ToolsResponse, ToolCallView
from app.core.trace import new_trace_id

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(state: AppState = Depends(get_app_state)) -> HealthResponse:
    """同步接口示例：健康检查不需要等待外部服务，所以用普通 def 即可。"""
    return HealthResponse(
        status="ok",
        service=state.settings.app_name,
        environment=state.settings.environment,
    )


@router.get("/tools", response_model=ToolsResponse)
def list_tools(state: AppState = Depends(get_app_state)) -> ToolsResponse:
    """同步接口示例：返回当前注册工具的名称、说明和参数结构。"""
    return ToolsResponse(
        tools=[
            ToolInfo(
                name=tool.name,
                description=tool.description,
                parameters_schema=tool.parameters_schema(),
            )
            for tool in state.tools.list_tools()
        ]
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, state: AppState = Depends(get_app_state)) -> ChatResponse:
    """异步接口示例：Agent 未来可能调用 LLM、数据库、HTTP 服务，所以这里使用 async。"""
    trace_id = new_trace_id()
    result = await state.agent.run(
        message=request.message,
        trace_id=trace_id,
        session_id=request.session_id,
        max_steps=request.max_steps,
    )

    return ChatResponse(
        answer=result.answer,
        used_tools=result.used_tools,
        trace_id=result.trace_id,
        tool_calls=[
            ToolCallView(
                name=call.name,
                arguments=call.arguments,
                result=call.result,
            )
            for call in result.tool_calls
        ],
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, state: AppState = Depends(get_app_state)) -> StreamingResponse:
    """Streaming 接口示例：使用 SSE 逐段返回 Agent 执行过程。"""
    trace_id = new_trace_id()

    async def event_source() -> AsyncIterator[str]:
        async for event in state.agent.stream(
            message=request.message,
            trace_id=trace_id,
            session_id=request.session_id,
            max_steps=request.max_steps,
        ):
            payload = json.dumps(event.model_dump(), ensure_ascii=False)
            yield f"event: {event.event}\ndata: {payload}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
