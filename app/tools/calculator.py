import ast
import operator

from pydantic import BaseModel, Field

from typing import Callable

from app.core.errors import AppError, ErrorCode
from app.tools.base import BaseTool, ToolResult


class CalculatorArgs(BaseModel):
    expression: str = Field(..., min_length=1, max_length=120, description="只包含数字和四则运算符的表达式")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "执行安全的四则运算表达式计算。"
    args_model = CalculatorArgs

    async def arun(self, arguments: dict[str, object], trace_id: str) -> ToolResult:
        args = self.validate_arguments(arguments, trace_id)
        assert isinstance(args, CalculatorArgs)
        value = safe_eval(args.expression, trace_id)
        return ToolResult(output=str(value), data={"value": value, "expression": args.expression})


def safe_eval(expression: str, trace_id: str) -> float:
    """使用 AST 白名单实现安全计算。

    TODO 练习 6：
    现在只支持 +、-、*、/ 和括号。请尝试加入：
    - 幂运算，但限制指数范围。
    - 一元正号。
    - 更友好的错误提示。
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, "数学表达式语法错误", trace_id=trace_id) from exc

    return _eval_node(tree.body, trace_id)

BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

def _eval_node(node: ast.AST, trace_id: str) -> float:


    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)

    if isinstance(node, ast.BinOp):
        operator_func = BINARY_OPERATORS.get(type(node.op))
        if operator_func is None:
            raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, f"不支持的数学运算符: {node.op.__str__()}", trace_id=trace_id)
        left = _eval_node(node.left, trace_id)
        right = _eval_node(node.right, trace_id)
        return operator_func(left, right)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand, trace_id)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return +_eval_node(node.operand, trace_id)

    raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, f"表达式包含不允许的内容: {node.__str__()}", trace_id=trace_id)

