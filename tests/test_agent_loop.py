import pytest

from app.agent.loop import AgentService
from app.core.config import Settings
from app.core.errors import AppError
from app.tools.calculator import CalculatorTool
from app.tools.file_search import FileSearchTool
from app.tools.registry import ToolRegistry
from app.tools.todo import TodoStore, TodoTool
from app.tools.web_summary_mock import WebSummaryMockTool


@pytest.mark.asyncio
async def test_agent_uses_calculator() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    agent = AgentService(registry, Settings())

    result = await agent.run("计算 2 + 3 * 4", trace_id="trace_test")

    assert result.answer == "计算结果：14.0"
    assert result.used_tools == ["calculator"]


@pytest.mark.asyncio
async def test_agent_respects_max_steps() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(TodoTool(TodoStore()))
    agent = AgentService(registry, Settings())

    with pytest.raises(AppError):
        await agent.run("计算 1 + 2 然后添加待办 写测试", trace_id="trace_test", max_steps=1)


@pytest.mark.asyncio
async def test_todo_isolated_by_session_id() -> None:
    registry = ToolRegistry()
    registry.register(TodoTool(TodoStore()))
    agent = AgentService(registry, Settings())

    await agent.run("添加待办 写文档", trace_id="trace_a", session_id="session_a")
    result = await agent.run("查看待办", trace_id="trace_b", session_id="session_b")

    assert result.answer == "待办事项结果：当前没有待办事项。"


@pytest.mark.asyncio
async def test_agent_runs_multiple_tool_calls_in_order() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(TodoTool(TodoStore()))
    agent = AgentService(registry, Settings())

    result = await agent.run("计算 1 + 2 然后添加待办 写测试", trace_id="trace_test", max_steps=2)

    assert result.used_tools == ["calculator", "todo"]
    assert len(result.tool_calls) == 2
    assert "已完成 2 个工具步骤" in result.answer


@pytest.mark.asyncio
async def test_agent_returns_clarification_for_empty_file_search_query() -> None:
    registry = ToolRegistry()
    registry.register(FileSearchTool(Settings().file_search_root))
    agent = AgentService(registry, Settings())

    result = await agent.run("搜索文件", trace_id="trace_test")

    assert result.used_tools == []
    assert "没有说明关键词" in result.answer


@pytest.mark.asyncio
async def test_agent_uses_web_summary_mock_for_url() -> None:
    registry = ToolRegistry()
    registry.register(WebSummaryMockTool())
    agent = AgentService(registry, Settings())

    result = await agent.run("帮我总结 https://example.com/post", trace_id="trace_test")

    assert result.used_tools == ["web_summary_mock"]
    assert "网页摘要" in result.answer
