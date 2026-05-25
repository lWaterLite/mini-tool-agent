from app.agent.prompts import build_tool_prompt
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


def test_build_tool_prompt_includes_schema() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    prompt = build_tool_prompt(registry)

    assert "工具名称：calculator" in prompt
    assert "参数 schema" in prompt
    assert "expression" in prompt
