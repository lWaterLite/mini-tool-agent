import pytest

from app.core.errors import AppError
from app.tools.calculator import safe_eval


def test_safe_eval_basic_expression() -> None:
    assert safe_eval("3 * (4 + 5)", "trace_test") == 27


def test_safe_eval_supports_limited_power_and_unary_plus() -> None:
    assert safe_eval("+2 ** 3", "trace_test") == 8


def test_safe_eval_rejects_too_large_power() -> None:
    with pytest.raises(AppError):
        safe_eval("2 ** 99", "trace_test")


def test_safe_eval_rejects_function_call() -> None:
    with pytest.raises(AppError):
        safe_eval("__import__('os').system('echo bad')", "trace_test")
