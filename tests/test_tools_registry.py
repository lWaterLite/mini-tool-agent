import pytest
import asyncio

from app.api.dependencies import build_tool_registry
from app.core.config import Settings
from app.core.errors import AppError
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry
from app.core.tool_settings import CalculatorSettings
from app.tools.todo import TodoStore


def test_registry_returns_registered_tool() -> None:
    registry = ToolRegistry()
    tool = CalculatorTool()

    registry.register(tool)

    assert registry.get("calculator") is tool


def test_registry_rejects_duplicate_tool_name() -> None:
    registry = ToolRegistry()
    registry.register(CalculatorTool())

    with pytest.raises(ValueError, match="工具名称重复"):
        registry.register(CalculatorTool())


def test_registry_raises_app_error_for_unknown_tool() -> None:
    registry = ToolRegistry()

    with pytest.raises(AppError) as exc_info:
        registry.get("missing_tool")

    assert exc_info.value.code == "TOOL_NOT_FOUND"


def test_build_tool_registry_injects_calculator_settings() -> None:
    settings = Settings(calculator_settings=CalculatorSettings(max_power_exponent=2))
    registry = build_tool_registry(settings, TodoStore())
    calculator = registry.get("calculator")

    with pytest.raises(AppError):
        asyncio.run(calculator.arun({"expression": "2 ** 3"}, trace_id="trace_test"))
