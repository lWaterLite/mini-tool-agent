import ast
import operator
from collections.abc import Callable

from pydantic import BaseModel, Field

from app.core.errors import AppError, ErrorCode
from app.tools.base import BaseTool, ToolResult
from app.core.tool_settings import CalculatorSettings

BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}


class CalculatorArgs(BaseModel):
    expression: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="只包含数字、括号、四则运算和受限幂运算的表达式",
    )


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "执行安全的数学表达式计算，支持 +、-、*、/、括号、一元正负号和受限幂运算。"
    args_model = CalculatorArgs

    def __init__(self, settings: CalculatorSettings | None = None) -> None:
        self._settings = settings or CalculatorSettings()

    def safe_eval(self, expression: str, trace_id: str) -> float:
        """使用 AST 白名单实现安全计算。

        只允许安全节点进入递归求值，不执行函数调用、属性访问、变量读取等任意代码。
        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, "数学表达式语法错误", trace_id=trace_id) from exc

        return self._eval_node(tree.body, trace_id)

    def _eval_node(self, node: ast.AST, trace_id: str) -> float:
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            return float(node.value)

        if isinstance(node, ast.BinOp):
            operator_func = BINARY_OPERATORS.get(type(node.op))
            if operator_func is None:
                raise AppError(
                    ErrorCode.TOOL_EXECUTION_ERROR,
                    f"不支持的数学运算符：{type(node.op).__name__}",
                    trace_id=trace_id,
                )
            left = self._eval_node(node.left, trace_id)
            right = self._eval_node(node.right, trace_id)
            if isinstance(node.op, ast.Div) and right == 0:
                raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, "除数不能为 0", trace_id=trace_id)
            if isinstance(node.op, ast.Pow) and abs(right) > self._settings.max_power_exponent:
                raise AppError(
                    ErrorCode.TOOL_EXECUTION_ERROR,
                    f"幂运算指数过大，指数绝对值不能超过 {self._settings.max_power_exponent}",
                    trace_id=trace_id,
                )
            try:
                return operator_func(left, right)
            except OverflowError as exc:
                raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, "计算结果过大", trace_id=trace_id) from exc

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -self._eval_node(node.operand, trace_id)

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            return +self._eval_node(node.operand, trace_id)

        if isinstance(node, ast.Name):
            raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, f"不允许使用变量：{node.id}", trace_id=trace_id)

        if isinstance(node, ast.Call):
            raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, "不允许调用函数", trace_id=trace_id)

        raise AppError(
            ErrorCode.TOOL_EXECUTION_ERROR,
            f"表达式包含不允许的内容：{type(node).__name__}",
            trace_id=trace_id,
        )

    async def arun(self, arguments: dict[str, object], trace_id: str) -> ToolResult:
        args = self.validate_arguments(arguments, trace_id)
        assert isinstance(args, CalculatorArgs)
        value = self.safe_eval(args.expression, trace_id)
        return ToolResult(output=str(value), data={"value": value, "expression": args.expression})


def safe_eval(
    expression: str,
    trace_id: str,
    settings: CalculatorSettings | None = None,
) -> float:
    """兼容函数式调用入口，内部仍然复用 CalculatorTool 的配置化实现。"""
    return CalculatorTool(settings).safe_eval(expression, trace_id)
