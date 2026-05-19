"""
子模块 2 练习脚本：Structured Output 与 Pydantic 校验。

练习目标：
1. 让模型输出结构化结果，而不是不可控自然语言。
2. 用 Pydantic 定义 AgentAction 模型。
3. 编写 parse_action(raw_text) 输出解析器。
4. 处理 JSON 解析失败、字段缺失、类型错误、范围错误和枚举错误。
5. 增加一次校验失败后的重试逻辑。

建议学习方式：
1. 先完整阅读本文件，理解每个 TODO 的目的。
2. 从 TODO 1 开始逐个完成，不要一次性改完所有内容。
3. 每完成一部分，运行：
       python submodule_2_exercise.py --demo
4. 最后再尝试运行：
       python submodule_2_exercise.py --self-check

注意：
- 本脚本刻意留下了较多练习题，不是一个完成版答案。
- 注释和题目是学习材料，核心代码需要你自己补完。
- 当前阶段不需要调用真实 LLM，所有模型输出都用字符串样例模拟。
"""

from __future__ import annotations

import argparse
import json
from typing import Any, Literal, Callable

try:
    from pydantic import BaseModel, Field, ValidationError, StrictBool
except ModuleNotFoundError as exc:
    raise SystemExit(
        "缺少依赖 pydantic。请先运行：\n"
        "  pip install pydantic\n"
        "或者使用项目虚拟环境运行本脚本。"
    ) from exc


# =============================================================================
# 第 1 部分：允许的 intent
# =============================================================================

# TODO 1：
# 这里先用 tuple 存放允许的 intent，方便你阅读。
# 请你思考：
# 1. 为什么不能让 intent 随便输出任意字符串？
#   因为随便输出的字符串不能符合后续可能的意图处理逻辑。
# 2. 如果模型输出 "search_file" 而不是 "file_search"，系统应该怎么办？
#   简单来说可以直接拒绝，返回错误并重试，如果希望扩大解析能力，可以尝试使用正则表达式，让search_file也匹配。
# 3. 后续是否应该用 Literal 限制 intent？
#   应该，这样做更加规范。
#
# 进阶任务：
# - 尝试把 AgentAction.intent 从 str 改成 Literal[...]。
# - 修改后观察错误样例 INVALID_INTENT_OUTPUT 的报错是否更清晰。
ALLOWED_INTENTS = (
    "chat",
    "calculator",
    "file_search",
    "web_summary",
    "todo",
)


# =============================================================================
# 第 2 部分：Pydantic 输出模型
# =============================================================================


class AgentAction(BaseModel):
    """模型对用户任务的结构化理解。

    你可以把这个类看成模型输出进入程序前必须通过的“安检口”。

    练习要求：
    - intent：用户意图。
    - arguments：该意图需要的参数。
    - confidence：模型置信度，应该在 0 到 1 之间。
    - need_tool：是否需要调用工具。
    """

    # TODO 2：
    # 当前 intent 只是 str，太宽松。
    # 练习：把它改成 Literal["chat", "calculator", "file_search", "web_summary", "todo"]。
    # 提示：你需要从 typing 导入 Literal。
    intent: Literal["chat", "calculator", "file_search", "web_summary", "todo"]

    # TODO 3：
    # arguments 应该是一个 dict。
    # 练习：
    # 1. 思考为什么 arguments 不应该是字符串。
    #   因为意图的参数可能有多个，用dict更合理。
    # 2. 给它保留 default_factory=dict 是否合理？
    #   合理，设置一个空dict默认值更方便后续处理。
    # 3. 如果 intent 是 calculator，arguments 里是否应该必须有 expression？
    #   应该有，calculator是计算意图，那么必须计算一个表达式。
    arguments: dict[str, Any]

    # TODO 4：
    # confidence 当前只有类型，没有范围约束。
    # 练习：使用 Field(ge=0, le=1) 限制它必须在 0 到 1 之间。
    confidence: float = Field(ge=0, le=1)

    # TODO 5：
    # need_tool 当前是 bool。
    # 练习：观察当模型输出 "yes"、"false"、1 时，Pydantic 会如何处理。
    # 思考：这里是否需要严格布尔类型？
    need_tool: StrictBool


# =============================================================================
# 第 3 部分：解析错误类型
# =============================================================================


class OutputParseError(ValueError):
    """模型输出解析失败。

    这个异常用于包装 JSON 解析失败和 Pydantic 校验失败。
    后续做重试时，可以把它的错误消息反馈给模型。
    """


# =============================================================================
# 第 4 部分：结构化输出 prompt
# =============================================================================


STRUCTURED_OUTPUT_PROMPT_TEMPLATE = """
你是一个任务解析器。
请把用户输入解析成一个 JSON 对象。

要求：
1. 只输出 JSON，不要输出 Markdown 代码块。
2. 不要添加解释文字。
3. 必须包含字段：intent、arguments、confidence、need_tool。
4. confidence 必须是 0 到 1 之间的数字。
5. need_tool 必须是 true 或 false。
6. 当intent设置为calculator时，arguments对象中必须包含expression字段。
7. 当intent设置为file_search时，arguments对象中必须包含query字段和directory字段。

允许的 intent：
- chat
- calculator
- file_search
- web_summary
- todo

合法的输出示例：
{{
    "intent": "chat",
    "arguments": {{}},
    "confidence": 0.9,
    "need_tool": false
}}

用户输入：
{user_input}
""".strip()


def build_structured_output_prompt(user_input: str) -> str:
    """根据用户输入生成结构化输出 prompt。

    TODO 6：
    这是一个相对简单的 prompt 模板函数。
    请你尝试改进它：
    1. 加入 1 个合法输出示例。
    2. 明确 calculator 的 arguments 应该包含 expression。
    3. 明确 file_search 的 arguments 应该包含 query 和 directory。
    4. 思考：示例会不会让模型过度模仿固定字段？
    """

    return STRUCTURED_OUTPUT_PROMPT_TEMPLATE.format(user_input=user_input)


# =============================================================================
# 第 5 部分：输出解析器
# =============================================================================


def parse_action(raw_text: str) -> AgentAction:
    """把模型原始输出解析成 AgentAction。

    TODO 7：完成这个函数。

    你需要实现：
    1. 使用 json.loads(raw_text) 把字符串解析成 Python dict。
    2. 如果 JSON 解析失败，抛出 OutputParseError，并说明错误原因。
    3. 使用 AgentAction.model_validate(data) 做 Pydantic 校验。
    4. 如果 Pydantic 校验失败，抛出 OutputParseError，并说明错误原因。
    5. 如果成功，返回 AgentAction 对象。

    参考结构：

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise OutputParseError(...) from exc

        try:
            return AgentAction.model_validate(data)
        except ValidationError as exc:
            raise OutputParseError(...) from exc

    思考题：
    - JSON 解析失败和 Pydantic 校验失败有什么区别？
    - 错误消息应该给开发者看，还是给模型看？两者有什么不同？
    """

    try:
        json_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise OutputParseError(f"模型输出不是合法JSON：{e}") from e

    try:
        return AgentAction.model_validate(json_data)
    except ValidationError as e:
        raise OutputParseError(f"模型输出字段校验失败：{e}") from e


# =============================================================================
# 第 6 部分：失败重试
# =============================================================================


def build_retry_prompt(user_input: str, bad_output: str, error_message: str) -> str:
    """构造校验失败后的重试 prompt。

    TODO 8：
    这个函数已经给出基础版本。
    请你思考并改进：
    1. 是否应该包含用户原始输入？
    应该包括
    2. 是否应该包含模型上一次的错误输出？
    应该包含
    3. 错误信息应该原样贴给模型，还是做简化？
    原样返回
    4. 如何强调“只输出 JSON”？
    """

    return f"""
你上一次输出不符合结构化格式要求。

用户原始输入：
{user_input}

你上一次的输出：
{bad_output}

解析或校验错误：
{error_message}

请重新输出一个纯 JSON 对象。
要求：
1. 不要输出 Markdown 代码块。
2. 不要添加解释文字。
3. 必须包含字段：intent、arguments、confidence、need_tool。
4. confidence 必须是 0 到 1 之间的数字。
5. need_tool 必须是 true 或 false。
""".strip()


def parse_with_one_retry(
    user_input: str,
    first_raw_output: str,
    retry_output_provider: Callable[[str], str],
) -> AgentAction:
    """解析模型输出；如果第一次失败，允许重试一次。

    retry_output_provider 是一个模拟函数，用来代替真实 LLM。
    它接收 retry_prompt，返回第二次模型输出。

    TODO 9：完成一次重试逻辑。

    你需要实现：
    1. 先调用 parse_action(first_raw_output)。
    2. 如果成功，直接返回。
    3. 如果失败，使用 build_retry_prompt 构造重试 prompt。
    4. 调用 retry_output_provider(retry_prompt) 获取第二次输出。
    5. 再次调用 parse_action(second_raw_output)。
    6. 第二次还失败时，让错误继续抛出。

    思考题：
    - 为什么这里只重试一次？
    - 如果重试也失败，应该返回 None、抛异常，还是返回错误对象？
    - 真实项目里是否应该记录 first_raw_output 和 retry_prompt？
    """

    try:
        return parse_action(first_raw_output)
    except OutputParseError as e:
       second_raw_output = retry_output_provider(build_retry_prompt(user_input, first_raw_output, e.__str__()))
       return parse_action(second_raw_output)


# =============================================================================
# 第 7 部分：样例输出
# =============================================================================


VALID_CALCULATOR_OUTPUT = """
{
  "intent": "calculator",
  "arguments": {
    "expression": "19 * 23 + 7"
  },
  "confidence": 0.96,
  "need_tool": true
}
""".strip()


VALID_CHAT_OUTPUT = """
{
  "intent": "chat",
  "arguments": {},
  "confidence": 0.82,
  "need_tool": false
}
""".strip()


# 错误样例 1：不是合法 JSON。
INVALID_JSON_OUTPUT = """
用户想要计算，所以结果是：
{
  "intent": "calculator",
  "arguments": {"expression": "1 + 2"},
  "confidence": 0.9,
  "need_tool": true
}
""".strip()


# 错误样例 2：缺少字段 confidence。
MISSING_FIELD_OUTPUT = """
{
  "intent": "calculator",
  "arguments": {
    "expression": "1 + 2"
  },
  "need_tool": true
}
""".strip()


# 错误样例 3：字段类型错误。
TYPE_ERROR_OUTPUT = """
{
  "intent": "calculator",
  "arguments": "1 + 2",
  "confidence": "high",
  "need_tool": "yes"
}
""".strip()


# 错误样例 4：confidence 超出范围。
CONFIDENCE_RANGE_ERROR_OUTPUT = """
{
  "intent": "calculator",
  "arguments": {
    "expression": "1 + 2"
  },
  "confidence": 1.5,
  "need_tool": true
}
""".strip()


# 错误样例 5：intent 不在允许范围内。
INVALID_INTENT_OUTPUT = """
{
  "intent": "search_file",
  "arguments": {
    "query": "RAG evaluation",
    "directory": "notes"
  },
  "confidence": 0.88,
  "need_tool": true
}
""".strip()


EXERCISE_CASES = [
    ("合法计算器输出", VALID_CALCULATOR_OUTPUT, True),
    ("合法普通聊天输出", VALID_CHAT_OUTPUT, True),
    ("非法 JSON", INVALID_JSON_OUTPUT, False),
    ("缺少字段", MISSING_FIELD_OUTPUT, False),
    ("类型错误", TYPE_ERROR_OUTPUT, False),
    ("confidence 超出范围", CONFIDENCE_RANGE_ERROR_OUTPUT, False),
    ("intent 不在允许范围内", INVALID_INTENT_OUTPUT, False),
]


# =============================================================================
# 第 8 部分：模拟重试输出
# =============================================================================


def fake_retry_output_provider(retry_prompt: str) -> str:
    """模拟 LLM 在收到错误反馈后重新生成输出。

    这里故意不调用真实模型，方便你测试重试流程。

    TODO 10：
    请你阅读 retry_prompt，思考：
    1. 如果真实模型看到这个 prompt，是否知道自己错在哪里？
    2. 如果错误是 intent 不合法，应该如何引导模型从允许列表中选择？
    3. 如果错误是 JSON 前后带解释文字，应该如何强调纯 JSON？
    """

    # 这里为了练习重试流程，固定返回一个合法结果。
    return VALID_CALCULATOR_OUTPUT


# =============================================================================
# 第 9 部分：演示与自检
# =============================================================================


def print_prompt_demo() -> None:
    """展示结构化输出 prompt。"""

    user_input = "帮我计算 19 * 23 + 7。"
    prompt = build_structured_output_prompt(user_input)
    print("\n=== 结构化输出 Prompt 示例 ===")
    print(prompt)


def run_demo() -> None:
    """运行解析器演示。

    在你完成 TODO 7 前，这个函数会提示 NotImplementedError。
    完成 TODO 7 后，你应该能看到合法样例解析成功，错误样例解析失败。
    """

    print("\n=== 输出解析演示 ===")
    for name, raw_text, should_pass in EXERCISE_CASES:
        print(f"\n用例：{name}")
        print(f"期望：{'解析成功' if should_pass else '解析失败'}")
        try:
            action = parse_action(raw_text)
        except NotImplementedError as exc:
            print(f"尚未实现：{exc}")
            return
        except OutputParseError as exc:
            print(f"实际：解析失败")
            print(f"错误：{exc}")
        else:
            print("实际：解析成功")
            print(action.model_dump())


def run_retry_demo() -> None:
    """运行一次重试演示。

    在你完成 TODO 7 和 TODO 9 后，这个函数应该能够：
    1. 发现第一次输出不是合法 JSON。
    2. 构造 retry prompt。
    3. 使用 fake_retry_output_provider 拿到第二次输出。
    4. 成功解析第二次输出。
    """

    print("\n=== 一次重试演示 ===")
    try:
        action = parse_with_one_retry(
            user_input="帮我计算 1 + 2。",
            first_raw_output=INVALID_JSON_OUTPUT,
            retry_output_provider=fake_retry_output_provider,
        )
    except NotImplementedError as exc:
        print(f"尚未实现：{exc}")
    except OutputParseError as exc:
        print(f"重试后仍然失败：{exc}")
    else:
        print("重试后解析成功：")
        print(action.model_dump())


def run_self_check() -> None:
    """运行自检。

    TODO 11：
    当你完成 TODO 7、TODO 9，并强化 AgentAction 字段约束后，
    请让这些检查全部符合预期。

    注意：
    - 这不是 pytest，只是一个轻量级自检入口。
    - 后续你可以把这些用例迁移到 tests/test_output_parser.py。
    """

    print("\n=== 自检开始 ===")
    passed_count = 0
    failed_count = 0

    for name, raw_text, should_pass in EXERCISE_CASES:
        try:
            parse_action(raw_text)
            actual_pass = True
        except OutputParseError:
            actual_pass = False

        if actual_pass == should_pass:
            passed_count += 1
            print(f"[通过] {name}")
        else:
            failed_count += 1
            print(f"[失败] {name}：期望 {should_pass}，实际 {actual_pass}")

    print(f"\n自检结果：通过 {passed_count} 个，失败 {failed_count} 个")

    if failed_count:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="子模块 2：结构化输出与 Pydantic 校验练习。")
    parser.add_argument("--prompt", action="store_true", help="展示结构化输出 prompt 示例。")
    parser.add_argument("--demo", action="store_true", help="运行输出解析演示。")
    parser.add_argument("--retry-demo", action="store_true", help="运行一次重试演示。")
    parser.add_argument("--self-check", action="store_true", help="运行轻量级自检。")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""

    args = parse_args()

    if args.prompt:
        print_prompt_demo()

    if args.demo:
        run_demo()

    if args.retry_demo:
        run_retry_demo()

    if args.self_check:
        run_self_check()

    if not any((args.prompt, args.demo, args.retry_demo, args.self_check)):
        print("请传入一个选项，例如：")
        print("  python submodule_2_exercise.py --prompt")
        print("  python submodule_2_exercise.py --demo")
        print("  python submodule_2_exercise.py --retry-demo")
        print("  python submodule_2_exercise.py --self-check")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
