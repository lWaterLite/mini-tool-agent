import pytest

from app.agent.loop import AgentService
from app.core.config import Settings
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_agent_uses_calculator() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    agent = AgentService(registry, Settings())

    result = await agent.run("计算 2 + 3 * 4", trace_id="trace_test")

    assert result.answer == "计算结果：14.0"
    assert result.used_tools == ["calculator"]

