"""子模块 4 练习入口。"""

from __future__ import annotations

import argparse
import json

from exercise.submodule_4_exercise.loop import MiniAgent
from exercise.submodule_4_exercise.mock_llm import DEFAULT_USER_INPUTS, SCRIPTS, ScriptedLLM


def list_scripts() -> None:
    """列出可用模拟脚本。"""

    print("\n=== 可用模拟脚本 ===")
    for name in SCRIPTS:
        print(f"- {name}: {DEFAULT_USER_INPUTS.get(name, '')}")


def run_demo(script_name: str, max_steps: int) -> None:
    """运行指定模拟脚本。"""

    if script_name not in SCRIPTS:
        raise SystemExit(f"未知脚本：{script_name}")

    user_input = DEFAULT_USER_INPUTS[script_name]
    agent = MiniAgent(
        llm=ScriptedLLM(outputs=list(SCRIPTS[script_name])),
        max_steps=max_steps,
    )

    print(f"\n=== 运行脚本：{script_name} ===")
    print(f"用户输入：{user_input}")

    try:
        result = agent.run(user_input)
    except NotImplementedError as exc:
        print(f"尚未实现：{exc}")
        return

    print("\n=== 执行结果 ===")
    print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))


def run_self_check() -> None:
    """轻量级自检。

    TODO 10：
    当你完成 TODO 1-9 后，让这些检查全部通过。

    覆盖场景：
    1. 单工具调用：calculator。
    2. 两次工具调用：todo add + todo list。
    3. 未知工具：应该失败。
    4. 模型输出坏 JSON：应该失败。
    5. max_steps：应该失败。
    """

    checks: list[tuple[str, bool]] = []

    try:
        calculator_result = MiniAgent(
            llm=ScriptedLLM(outputs=list(SCRIPTS["calculator"])),
            max_steps=5,
        ).run(DEFAULT_USER_INPUTS["calculator"])
        checks.append((
            "calculator 单工具调用成功",
            calculator_result.ok and "444" in calculator_result.final_answer,
        ))

        todo_result = MiniAgent(
            llm=ScriptedLLM(outputs=list(SCRIPTS["todo_two_steps"])),
            max_steps=5,
        ).run(DEFAULT_USER_INPUTS["todo_two_steps"])
        tool_steps = [s for s in todo_result.steps if s.get("event") == "tool_call"]
        checks.append((
            "todo 两次工具调用成功",
            todo_result.ok and len(tool_steps) == 2,
        ))

        unknown_tool_result = MiniAgent(
            llm=ScriptedLLM(outputs=list(SCRIPTS["unknown_tool"])),
            max_steps=5,
        ).run(DEFAULT_USER_INPUTS["unknown_tool"])
        checks.append((
            "未知工具会失败",
            not unknown_tool_result.ok and unknown_tool_result.error is not None,
        ))

        bad_json_result = MiniAgent(
            llm=ScriptedLLM(outputs=list(SCRIPTS["bad_json"])),
            max_steps=5,
        ).run(DEFAULT_USER_INPUTS["bad_json"])
        checks.append((
            "模型坏 JSON 会失败",
            not bad_json_result.ok and bad_json_result.error is not None,
        ))

        max_steps_result = MiniAgent(
            llm=ScriptedLLM(outputs=list(SCRIPTS["max_steps"])),
            max_steps=2,
        ).run(DEFAULT_USER_INPUTS["max_steps"])
        checks.append((
            "超过 max_steps 会失败",
            not max_steps_result.ok and max_steps_result.error is not None,
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

    parser = argparse.ArgumentParser(description="子模块 4：手写最小 Agent Loop 练习。")
    parser.add_argument("--list-scripts", action="store_true", help="列出可用模拟脚本。")
    parser.add_argument("--demo", choices=sorted(SCRIPTS.keys()), help="运行一个模拟脚本。")
    parser.add_argument("--max-steps", type=int, default=5, help="最大循环轮数。")
    parser.add_argument("--self-check", action="store_true", help="运行轻量级自检。")
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""

    args = parse_args()

    if args.list_scripts:
        list_scripts()

    if args.demo:
        run_demo(args.demo, args.max_steps)

    if args.self_check:
        run_self_check()

    if not any((args.list_scripts, args.demo, args.self_check)):
        print("请传入一个选项，例如：")
        print("  python -m exercise.submodule_4_exercise.demo --list-scripts")
        print("  python -m exercise.submodule_4_exercise.demo --demo calculator")
        print("  python -m exercise.submodule_4_exercise.demo --self-check")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
