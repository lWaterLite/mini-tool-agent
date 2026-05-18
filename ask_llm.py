"""
子模块 1 练习：从命令行调用一次 LLM。

这个示例覆盖：
1. 从命令行读取用户输入。
2. 从环境变量或 .env 文件读取 API key 和模型配置。
3. 构造 system + user messages。
4. 调用 OpenAI 兼容的聊天 API。
5. 允许调用者调整 temperature 和 max tokens。
6. 可选使用流式输出打印回答。

运行示例：
    python ask_llm.py "什么是 agent loop？"
    python ask_llm.py --temperature 0.0 "用三句话解释 temperature"
    python ask_llm.py --stream "请像技术助教一样解释 streaming"

运行前准备：
    1. 安装 SDK：pip install openai
    2. 复制 .env.example 为 .env
    3. 填写 LLM_API_KEY 和 LLM_MODEL
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - 这里用于提供更友好的运行时提示。
    OpenAI = None  # type: ignore[assignment]

DEFAULT_SYSTEM_PROMPT = (
    "你是一个严谨、耐心的技术助教。"
    "请优先用中文回答；解释技术概念时先给定义，再说明作用，最后给一个简单例子。"
)

LOGGER = logging.getLogger("ask_llm")


class ConfigError(RuntimeError):
    """当必要运行配置缺失或不合法时抛出。"""


@dataclass(frozen=True)
class LLMConfig:
    """一次 LLM 请求所需的运行配置。

    把配置集中放在一个对象里，可以让代码更容易测试和扩展。
    后续完整 agent 项目中，这个思路可以演进为 app/core/config.py。
    """

    api_key: str
    model: str
    base_url: str | None
    temperature: float
    max_tokens: int
    stream: bool


def load_dotenv(dotenv_path: Path) -> None:
    """从 .env 文件中读取简单的 KEY=VALUE 配置。

    第一个练习先不引入 python-dotenv，所以这里写一个很小的读取器。
    它只处理最常见的情况，并且不会覆盖已经存在的环境变量：
    命令行或系统环境中显式提供的值，应该优先于本地 .env 默认值。
    """

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        # 空行和注释可以让 .env 文件更容易阅读。
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            LOGGER.warning("跳过不合法的 .env 行：%s", raw_line)
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def read_float_env(name: str, default: float) -> float:
    """读取浮点数环境变量，并在格式错误时给出清晰提示。"""

    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} 必须是数字，当前值为：{value!r}") from exc


def read_int_env(name: str, default: int) -> int:
    """读取整数环境变量，并在格式错误时给出清晰提示。"""

    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} 必须是整数，当前值为：{value!r}") from exc


def build_config(args: argparse.Namespace) -> LLMConfig:
    """把命令行参数和环境变量合并成一个配置对象。"""

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConfigError(
            "缺少 API key。请在 .env 或系统环境变量中设置 LLM_API_KEY。"
        )

    model = args.model or os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
    if not model:
        raise ConfigError("缺少模型名称。请在 .env 中设置 LLM_MODEL，或传入 --model。")

    temperature = (
        args.temperature
        if args.temperature is not None
        else read_float_env("LLM_TEMPERATURE", 0.3)
    )
    max_tokens = (
        args.max_tokens
        if args.max_tokens is not None
        else read_int_env("LLM_MAX_TOKENS", 800)
    )

    if not 0 <= temperature <= 2:
        raise ConfigError("temperature 必须在 0 到 2 之间。")

    if max_tokens <= 0:
        raise ConfigError("max_tokens 必须大于 0。")

    base_url = args.base_url or os.getenv("LLM_BASE_URL") or None

    return LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=args.stream,
    )


def build_messages(system_prompt: str) -> list[dict[str, str]]:
    """构造发送给模型的 messages 列表。

    子模块 1 中，我们只需要 system + user 两类消息。
    后续进入 agent loop 后，还会加入 assistant 消息和 tool 结果消息。
    """
    return [
        {"role": "system", "content": system_prompt}
    ]


def create_client(config: LLMConfig) -> Any:
    """创建 LLM 客户端。

    OpenAI SDK 在配置 base_url 后，也可以调用很多 OpenAI 兼容供应商。
    这样后续切换模型服务时，不需要改动其他调用代码。
    """

    if OpenAI is None:
        raise ConfigError("未安装 openai 包。请先运行：pip install openai")

    if config.base_url:
        return OpenAI(api_key=config.api_key, base_url=config.base_url)

    return OpenAI(api_key=config.api_key)


def ask_once(client: Any, config: LLMConfig, messages: list[dict[str, str]]) -> str:
    """发送一次非流式聊天请求，并返回 assistant 文本。"""

    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("模型返回了空响应。")

    return content


def ask_stream(client: Any, config: LLMConfig, messages: list[dict[str, str]]) -> str:
    """发送一次流式聊天请求，并在内容到达时逐段打印。"""

    chunks: list[str] = []
    stream = client.chat.completions.create(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        stream=True,
    )

    for event in stream:
        delta = event.choices[0].delta.content or ""
        if not delta:
            continue

        print(delta, end="", flush=True)
        chunks.append(delta)

    print()
    return "".join(chunks)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。

    question 是可选的位置参数。
    你既可以启动时直接传入问题，也可以启动后在交互提示中输入。
    """

    parser = argparse.ArgumentParser(description="向 LLM 提出一个问题。")
    parser.add_argument("question", nargs="*", help="要发送给模型的问题。")
    parser.add_argument("--model", help="仅在本次运行中覆盖 LLM_MODEL。")
    parser.add_argument("--base-url", help="仅在本次运行中覆盖 LLM_BASE_URL。")
    parser.add_argument(
        "--temperature",
        type=float,
        help="采样温度。越低越稳定，越高越有创造性。",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="最大输出 token 数。",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="模型生成时逐段打印回答。",
    )
    parser.add_argument(
        "--system-prompt",
        default=DEFAULT_SYSTEM_PROMPT,
        help="覆盖默认的技术助教 system prompt。",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="环境变量文件路径。默认读取当前目录下的 .env。",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="打印调试日志。程序不会记录 API key。",
    )
    parser.add_argument(
        "--save",
        type=str,
        help="将模型回答存储为输入字符名称的Markdown文件，只保存最终对话回答。"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="进入交互式对话。")
    return parser.parse_args(argv)


def get_question(args: argparse.Namespace) -> str:
    """从命令行参数或交互输入中获取用户问题。"""

    if args.question:
        return " ".join(args.question).strip()

    return input("请输入你的问题：").strip()


def main(argv: list[str] | None = None) -> int:
    """程序入口。

    这里返回退出码，而不是在各处直接调用 sys.exit，
    这样后续用 pytest 测试 main 函数会更方便。
    """

    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(name)s - %(message)s",
    )

    try:
        load_dotenv(Path(args.env_file))
        config = build_config(args)
        LOGGER.debug("使用模型=%s，是否流式输出=%s", config.model, config.stream)
        LOGGER.debug(f"是否启用交互式对话: {args.chat}")
        cost_time: float = 0.0
        answer = None
        client = create_client(config)
        question = get_question(args).strip()
        messages = build_messages(args.system_prompt)
        if args.chat:
            while question.strip().lower() != "exit":
                if not question:
                    raise ConfigError("问题不能为空。")

                messages.append({"role": "user", "content": question})

                LOGGER.debug("messages 数量=%d", len(messages))

                start = time.perf_counter()
                if config.stream:
                    answer = ask_stream(client, config, messages)
                else:
                    answer = ask_once(client, config, messages)
                    print(answer)
                end = time.perf_counter()

                cost_time += end - start

                messages.append({"role": "assistant", "content": answer})

                question = input("请继续输入对话: ")
        else:
            start = time.perf_counter()
            if config.stream:
                answer = ask_stream(client, config, messages)
            else:
                answer = ask_once(client, config, messages)
                print(answer)
            end = time.perf_counter()
            cost_time += end - start

        if args.save and answer is not None:
            Path(args.save).write_text(answer, encoding="utf-8")

        print(f"请求耗时{cost_time: .2f}秒")

        return 0

    except KeyboardInterrupt:
        print("\n用户中断了程序。", file=sys.stderr)
        return 130
    except ConfigError as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # 第一个练习先让运行时错误保持易读。
        print(f"请求失败：{exc}", file=sys.stderr)
        return 1


# 留给你的练习任务：
# 1. 增加一个 --save 选项，把最终回答写入 Markdown 文件。
# 2. 增加一个 --repeat N 选项，多次询问同一个问题，并比较
#    temperature 如何影响回答稳定性。
# 3. 增加一个简单对话模式：在用户输入 "exit" 前，把之前的 assistant
#    回复持续保留在 messages 中。
# 4. 记录请求耗时，但不要记录 API key 或完整用户消息。


if __name__ == "__main__":
    raise SystemExit(main())
