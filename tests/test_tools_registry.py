import pytest

from app.core.errors import AppError
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


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

