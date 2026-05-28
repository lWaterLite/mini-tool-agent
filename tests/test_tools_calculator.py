import pytest

from app.core.errors import AppError
from app.tools.calculator import CalculatorTool, safe_eval
from app.core.tool_settings import CalculatorSettings


def test_safe_eval_basic_expression() -> None:
    assert safe_eval("3 * (4 + 5)", "trace_test") == 27


def test_safe_eval_supports_limited_power_and_unary_plus() -> None:
    assert safe_eval("+2 ** 3", "trace_test") == 8


def test_safe_eval_rejects_too_large_power() -> None:
    with pytest.raises(AppError):
        safe_eval("2 ** 99", "trace_test")


def test_safe_eval_uses_custom_power_exponent_limit() -> None:
    settings = CalculatorSettings(max_power_exponent=2)

    with pytest.raises(AppError) as exc_info:
        safe_eval("2 ** 3", "trace_test", settings)

    assert "指数绝对值不能超过 2" in exc_info.value.message


def test_calculator_tool_uses_injected_settings() -> None:
    tool = CalculatorTool(CalculatorSettings(max_power_exponent=3))

    assert tool.safe_eval("2 ** 3", "trace_test") == 8
    with pytest.raises(AppError):
        tool.safe_eval("2 ** 4", "trace_test")


def test_safe_eval_rejects_division_by_zero() -> None:
    with pytest.raises(AppError) as exc_info:
        safe_eval("1 / 0", "trace_test")

    assert exc_info.value.code == "TOOL_EXECUTION_ERROR"


def test_safe_eval_rejects_variable_name() -> None:
    with pytest.raises(AppError) as exc_info:
        safe_eval("a + 1", "trace_test")

    assert exc_info.value.code == "TOOL_EXECUTION_ERROR"


def test_safe_eval_rejects_function_call() -> None:
    with pytest.raises(AppError):
        safe_eval("__import__('os').system('echo bad')", "trace_test")
