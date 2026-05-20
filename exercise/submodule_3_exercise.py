"""
子模块 3 练习脚本：Tool Calling 与工具层设计。

练习目标：
1. 定义统一工具返回结构 ToolResult。
2. 为每个工具定义 Pydantic 参数模型。
3. 实现 4 类工具：计算器、文件检索、网页摘要 mock、待办事项。
4. 实现工具注册表，支持列出工具、查找工具、执行工具。
5. 练习工具参数校验、工具失败处理和工具测试思路。

建议学习方式：
1. 先完整阅读本文件，理解工具层和 agent loop 的边界。
2. 从 TODO 1 开始逐步完成，不要一次性写完全部工具。
3. 每完成一部分，运行：
       python exercise/submodule_3_exercise.py --demo
4. 最后运行：
       python exercise/submodule_3_exercise.py --self-check

注意：
- 本脚本仍然不调用真实 LLM。
- 当前练习重点是“工具层”，不是完整 agent loop。
- 真实模型选择工具的部分，会在子模块 4 再接上。
"""

from __future__ import annotations

import argparse
import ast
import json
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

try:
    from pydantic import BaseModel, Field, ValidationError, model_validator
except ModuleNotFoundError as exc:
    raise SystemExit(
        "缺少依赖 pydantic。请先运行：\n"
        "  pip install pydantic\n"
        "或者使用项目虚拟环境运行本脚本。"
    ) from exc


# =============================================================================
# 第 1 部分：通用工具返回结构
# =============================================================================


class ToolResult(BaseModel):
    """所有工具统一返回的结果结构。

    TODO 1：
    请阅读并思考：
    1. 为什么所有工具都应该返回同一种结构？
    2. ok、content、data、error 分别应该给谁用？
    3. 工具失败时，为什么不建议直接 raise 到最外层？
    """

    ok: bool
    content: str
    data: dict[str, Any] | None = None
    error: str | None = None


class ToolExecutionError(RuntimeError):
    """工具执行失败。

    练习中你可以选择：
    - 在工具内部捕获异常并返回 ToolResult(ok=False)
    - 或者让 registry 捕获 ToolExecutionError 后转成 ToolResult

    本脚本推荐：工具函数自己尽量返回 ToolResult，注册表负责兜底。
    """


# =============================================================================
# 第 2 部分：工具参数模型
# =============================================================================


class CalculatorArgs(BaseModel):
    """计算器工具参数。"""

    # TODO 2：
    # 练习：
    # 1. 给 expression 增加最小长度约束。
    # 2. 思考是否应该限制最大长度，为什么？
    # 3. 思考为什么 expression 不能直接交给 eval。
    expression: str = Field(description="要计算的数学表达式，例如 19 * 23 + 7")


class FileSearchArgs(BaseModel):
    """文件检索工具参数。"""

    # TODO 3：
    # 练习：
    # 1. 给 query 增加最小长度约束。
    # 2. 给 max_results 增加范围约束，例如 1 到 20。
    # 3. 思考 directory 为什么需要路径安全校验。
    query: str = Field(description="要搜索的关键词")
    directory: str = Field(description="要搜索的目录，必须位于项目根目录内")
    max_results: int = Field(default=5, description="最多返回多少条匹配结果")


class WebSummaryArgs(BaseModel):
    """网页摘要 mock 工具参数。"""

    # TODO 4：
    # 练习：
    # 1. 给 url 增加最小长度约束。
    # 2. 增加一个简单校验：url 必须以 http:// 或 https:// 开头。
    # 3. 思考真实网页工具为什么不应该在本阶段实现。
    url: str = Field(description="要摘要的网页 URL")


class TodoArgs(BaseModel):
    """待办事项工具参数。"""

    action: Literal["add", "list", "complete"]
    title: str | None = Field(default=None, description="新增待办时的标题")
    task_id: str | None = Field(default=None, description="完成待办时的任务 ID")

    # TODO 5：
    # 使用 model_validator 做跨字段校验：
    # 1. action == "add" 时，title 必须存在且不能为空。
    # 2. action == "complete" 时，task_id 必须存在且不能为空。
    # 3. action == "list" 时，不需要 title 或 task_id。
    #
    # 提示：
    #   @model_validator(mode="after")
    #   def validate_by_action(self) -> "TodoArgs":
    #       ...
    #       return self


# =============================================================================
# 第 3 部分：工具规格与注册表
# =============================================================================


@dataclass(frozen=True)
class ToolSpec:
    """工具规格。

    name：工具名称，模型会使用它来请求工具。
    description：工具描述，帮助模型理解何时使用它。
    args_model：工具参数 Pydantic 模型。
    handler：真正执行工具的函数。
    """

    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[BaseModel], ToolResult]

    def schema(self) -> dict[str, Any]:
        """返回工具 schema。

        TODO 6：
        当前 schema 足够练习，但你可以进一步思考：
        1. 这个 schema 是给模型看的，还是给 API 用户看的？
        2. 为什么 args_model.model_json_schema() 很适合放到 /tools 接口里？
        3. 是否应该把 description 写得更具体？
        """

        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_model.model_json_schema(),
        }


class ToolRegistry:
    """工具注册表。"""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        """注册工具。

        TODO 7：
        完成注册逻辑：
        1. 不允许重复注册同名工具。
        2. 注册成功后存入 self._tools。
        """

        raise NotImplementedError("TODO 7：请实现 ToolRegistry.register。")

    def list_tools(self) -> list[dict[str, Any]]:
        """列出当前可用工具 schema。"""

        return [tool.schema() for tool in self._tools.values()]

    def get(self, name: str) -> ToolSpec | None:
        """根据工具名称查找工具。"""

        return self._tools.get(name)

    def run(self, name: str, raw_args: dict[str, Any]) -> ToolResult:
        """执行工具。

        TODO 8：
        完成工具执行流程：
        1. 根据 name 查找工具；不存在时返回 ToolResult(ok=False)。
        2. 使用 spec.args_model.model_validate(raw_args) 校验参数。
        3. 参数校验失败时返回 ToolResult(ok=False)，error 写清楚原因。
        4. 参数合法时调用 spec.handler(args)。
        5. 捕获工具内部异常，转成 ToolResult(ok=False)。

        思考题：
        - 为什么 registry 要做工具白名单？
        - 为什么不能让模型直接传一个 Python 函数名来执行？
        """

        raise NotImplementedError("TODO 8：请实现 ToolRegistry.run。")


# =============================================================================
# 第 4 部分：计算器工具
# =============================================================================


ALLOWED_BIN_OPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

ALLOWED_UNARY_OPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_eval_math_expression(expression: str) -> float:
    """安全计算数学表达式。

    TODO 9：
    请完成一个基于 ast 的安全计算器。

    需要支持：
    - 数字
    - 加减乘除
    - 一元正负号
    - 括号

    必须拒绝：
    - 函数调用
    - 变量名
    - 属性访问
    - 导入
    - 幂运算等未允许操作

    提示：
    1. ast.parse(expression, mode="eval") 可以解析表达式。
    2. 递归处理 ast.Expression、ast.Constant、ast.BinOp、ast.UnaryOp。
    3. 对不认识的节点 raise ValueError。
    """

    raise NotImplementedError("TODO 9：请实现 safe_eval_math_expression。")


def run_calculator(args: BaseModel) -> ToolResult:
    """执行计算器工具。"""

    calculator_args = CalculatorArgs.model_validate(args)

    try:
        value = safe_eval_math_expression(calculator_args.expression)
    except Exception as exc:
        return ToolResult(
            ok=False,
            content="计算器工具执行失败。",
            error=str(exc),
        )

    return ToolResult(
        ok=True,
        content=f"计算结果是 {value}",
        data={"value": value, "expression": calculator_args.expression},
    )


# =============================================================================
# 第 5 部分：文件检索工具
# =============================================================================


def ensure_inside_root(root: Path, target: Path) -> Path:
    """确保 target 位于 root 内部。

    TODO 10：
    完成路径安全检查：
    1. root 和 target 都要 resolve。
    2. 如果 target 不在 root 内，抛出 ValueError。
    3. 返回 resolve 后的 target。

    提示：
    Python 3.9+ 可以使用 target.is_relative_to(root)。
    """

    raise NotImplementedError("TODO 10：请实现 ensure_inside_root。")


def iter_text_files(directory: Path) -> list[Path]:
    """列出目录中的 .md 和 .txt 文件。

    TODO 11：
    完成文件枚举：
    1. 递归搜索 directory 下的文件。
    2. 只返回后缀为 .md 或 .txt 的文件。
    3. 忽略目录和其他文件类型。
    """

    raise NotImplementedError("TODO 11：请实现 iter_text_files。")


def run_file_search(args: BaseModel) -> ToolResult:
    """执行文件检索工具。

    TODO 12：
    完成文件检索：
    1. 校验 FileSearchArgs。
    2. 以当前项目根目录作为 root。
    3. 确保 args.directory 不越过 root。
    4. 搜索 .md 和 .txt 文件。
    5. 找到包含 query 的行，返回 file、line、snippet。
    6. 最多返回 max_results 条。

    思考题：
    - query 是否应该大小写敏感？
    - snippet 应该返回整行，还是前后几行上下文？
    - 文件读取失败时应该跳过，还是返回错误？
    """

    raise NotImplementedError("TODO 12：请实现 run_file_search。")


# =============================================================================
# 第 6 部分：网页摘要 mock 工具
# =============================================================================


MOCK_WEB_SUMMARIES = {
    "https://example.com/agent-intro": {
        "title": "AI Agent 入门",
        "summary": "这篇文章介绍了 AI Agent 如何理解任务、调用工具并整合结果。",
    },
    "https://example.com/rag": {
        "title": "RAG 简介",
        "summary": "这篇文章介绍了 RAG 的加载、切分、向量化、检索和生成流程。",
    },
}


def run_web_summary_mock(args: BaseModel) -> ToolResult:
    """执行网页摘要 mock 工具。

    TODO 13：
    完成 mock 工具：
    1. 校验 WebSummaryArgs。
    2. 如果 URL 在 MOCK_WEB_SUMMARIES 中，返回对应摘要。
    3. 如果 URL 不存在，返回 ok=False，并说明这是 mock 数据未命中。

    思考题：
    - 为什么本阶段不做真实网页抓取？
    - mock 工具如何帮助你写稳定测试？
    """

    raise NotImplementedError("TODO 13：请实现 run_web_summary_mock。")


# =============================================================================
# 第 7 部分：待办事项工具
# =============================================================================


class InMemoryTodoStore:
    """内存版待办事项存储。

    这个类故意很小，用来练习工具状态管理。
    后续可以替换为 JSON 文件或 SQLite。
    """

    def __init__(self) -> None:
        self._tasks: list[dict[str, Any]] = []
        self._next_id = 1

    def add(self, title: str) -> dict[str, Any]:
        """新增待办。

        TODO 14：
        完成新增逻辑：
        1. 生成字符串 ID。
        2. 保存 title 和 done=False。
        3. 递增 self._next_id。
        4. 返回新任务 dict。
        """

        raise NotImplementedError("TODO 14：请实现 InMemoryTodoStore.add。")

    def list(self) -> list[dict[str, Any]]:
        """返回所有待办。"""

        return list(self._tasks)

    def complete(self, task_id: str) -> dict[str, Any] | None:
        """完成指定待办。

        TODO 15：
        完成任务：
        1. 根据 task_id 查找任务。
        2. 找到后把 done 改成 True。
        3. 返回任务。
        4. 找不到返回 None。
        """

        raise NotImplementedError("TODO 15：请实现 InMemoryTodoStore.complete。")


TODO_STORE = InMemoryTodoStore()


def run_todo(args: BaseModel) -> ToolResult:
    """执行待办事项工具。

    TODO 16：
    完成待办工具：
    1. 校验 TodoArgs。
    2. action == "add" 时新增任务。
    3. action == "list" 时列出任务。
    4. action == "complete" 时完成任务。
    5. 找不到任务时返回 ok=False。
    """

    raise NotImplementedError("TODO 16：请实现 run_todo。")


# =============================================================================
# 第 8 部分：默认工具注册
# =============================================================================


def build_default_registry() -> ToolRegistry:
    """构建默认工具注册表。

    TODO 17：
    在完成 ToolRegistry.register 后，取消下面注释并注册 4 个工具。
    """

    registry = ToolRegistry()

    # registry.register(
    #     ToolSpec(
    #         name="calculator",
    #         description="计算安全的数学表达式，支持加减乘除和括号。",
    #         args_model=CalculatorArgs,
    #         handler=run_calculator,
    #     )
    # )
    # registry.register(
    #     ToolSpec(
    #         name="file_search",
    #         description="在项目目录内搜索 .md 或 .txt 文件。",
    #         args_model=FileSearchArgs,
    #         handler=run_file_search,
    #     )
    # )
    # registry.register(
    #     ToolSpec(
    #         name="web_summary_mock",
    #         description="返回预设网页摘要，不访问真实网络。",
    #         args_model=WebSummaryArgs,
    #         handler=run_web_summary_mock,
    #     )
    # )
    # registry.register(
    #     ToolSpec(
    #         name="todo",
    #         description="管理待办事项，支持新增、查看、完成。",
    #         args_model=TodoArgs,
    #         handler=run_todo,
    #     )
    # )

    return registry


# =============================================================================
# 第 9 部分：演示与自检
# =============================================================================


def print_schema_demo() -> None:
    """展示工具 schema。"""

    registry = build_default_registry()
    print("\n=== 当前可用工具 ===")
    tools = registry.list_tools()
    if not tools:
        print("当前还没有注册工具。完成 TODO 7 和 TODO 17 后再运行。")
        return

    print(json.dumps(tools, ensure_ascii=False, indent=2))


def run_demo() -> None:
    """运行工具层演示。"""

    registry = build_default_registry()

    demo_calls = [
        ("calculator", {"expression": "19 * 23 + 7"}),
        ("web_summary_mock", {"url": "https://example.com/agent-intro"}),
        ("todo", {"action": "add", "title": "周五整理 mini-tool-agent README"}),
        ("todo", {"action": "list"}),
    ]

    print("\n=== 工具调用演示 ===")
    for tool_name, raw_args in demo_calls:
        print(f"\n调用工具：{tool_name}")
        print(f"参数：{raw_args}")
        try:
            result = registry.run(tool_name, raw_args)
        except NotImplementedError as exc:
            print(f"尚未实现：{exc}")
            return

        print(result.model_dump())


def run_self_check() -> None:
    """轻量级自检。

    TODO 18：
    当你完成所有工具后，让这些检查全部通过。
    后续可以把这些检查迁移到 pytest。
    """

    registry = build_default_registry()

    checks: list[tuple[str, bool]] = []

    try:
        checks.append(("工具数量为 4", len(registry.list_tools()) == 4))
        checks.append((
            "不存在的工具会失败",
            registry.run("missing_tool", {}).ok is False,
        ))
        checks.append((
            "计算器能计算表达式",
            registry.run("calculator", {"expression": "1 + 2 * 3"}).data == {"value": 7, "expression": "1 + 2 * 3"},
        ))
        checks.append((
            "计算器拒绝危险表达式",
            registry.run("calculator", {"expression": "__import__('os').system('echo bad')"}).ok is False,
        ))
        checks.append((
            "网页 mock 能命中预设摘要",
            registry.run("web_summary_mock", {"url": "https://example.com/agent-intro"}).ok is True,
        ))
        add_result = registry.run("todo", {"action": "add", "title": "学习 Tool Calling"})
        task_id = None
        if add_result.data and "task" in add_result.data:
            task_id = add_result.data["task"]["id"]
        checks.append(("待办 add 成功", add_result.ok is True and task_id is not None))
        checks.append((
            "待办 complete 成功",
            registry.run("todo", {"action": "complete", "task_id": task_id}).ok is True if task_id else False,
        ))
    except NotImplementedError as exc:
        print(f"尚未实现：{exc}")
        raise SystemExit(1) from exc

    print("\n=== 自检开始 ===")
    failed = 0
    for name, passed in checks:
        if passed:
            print(f"[通过] {name}")
        else:
            failed += 1
            print(f"[失败] {name}")

    if failed:
        print(f"\n自检结果：失败 {failed} 项")
        raise SystemExit(1)

    print("\n自检结果：全部通过")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="子模块 3：Tool Calling 与工具层设计练习。")
    parser.add_argument("--schema", action="store_true", help="展示工具 schema。")
    parser.add_argument("--demo", action="store_true", help="运行工具调用演示。")
    parser.add_argument("--self-check", action="store_true", help="运行轻量级自检。")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""

    args = parse_args()

    if args.schema:
        print_schema_demo()

    if args.demo:
        run_demo()

    if args.self_check:
        run_self_check()

    if not any((args.schema, args.demo, args.self_check)):
        print("请传入一个选项，例如：")
        print("  python exercise/submodule_3_exercise.py --schema")
        print("  python exercise/submodule_3_exercise.py --demo")
        print("  python exercise/submodule_3_exercise.py --self-check")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
