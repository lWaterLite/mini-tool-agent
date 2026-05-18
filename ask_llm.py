"""
Submodule 1 exercise: call an LLM from the command line.

What this example covers:
1. Read user input from the command line.
2. Read the API key and model settings from environment variables or .env.
3. Build system + user messages.
4. Call an OpenAI-compatible chat API.
5. Let the caller adjust temperature and max tokens.
6. Optionally print the answer as a stream.

Run examples:
    python ask_llm.py "什么是 agent loop？"
    python ask_llm.py --temperature 0.0 "用三句话解释 temperature"
    python ask_llm.py --stream "请像技术助教一样解释 streaming"

Before running:
    1. Install the SDK: pip install openai
    2. Copy .env.example to .env
    3. Fill in LLM_API_KEY and LLM_MODEL
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - this is a friendly runtime message.
    OpenAI = None  # type: ignore[assignment]


DEFAULT_SYSTEM_PROMPT = (
    "你是一个严谨、耐心的技术助教。"
    "请优先用中文回答；解释技术概念时先给定义，再说明作用，最后给一个简单例子。"
)

LOGGER = logging.getLogger("ask_llm")


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class LLMConfig:
    """Runtime settings for a single LLM request.

    Keeping configuration in one object makes the code easier to test and extend.
    Later, this idea can grow into app/core/config.py in the full agent project.
    """

    api_key: str
    model: str
    base_url: str | None
    temperature: float
    max_tokens: int
    stream: bool


def load_dotenv(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file.

    This tiny loader avoids adding python-dotenv for the first exercise. It only
    handles the common case and intentionally does not override real environment
    variables, because shell-provided values should win over local defaults.
    """

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        # Empty lines and comments keep .env files readable.
        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            LOGGER.warning("Skip invalid .env line: %s", raw_line)
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def read_float_env(name: str, default: float) -> float:
    """Read a float environment variable with a clear error message."""

    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got: {value!r}") from exc


def read_int_env(name: str, default: int) -> int:
    """Read an integer environment variable with a clear error message."""

    value = os.getenv(name)
    if value is None or value == "":
        return default

    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got: {value!r}") from exc


def build_config(args: argparse.Namespace) -> LLMConfig:
    """Merge CLI arguments and environment variables into one config object."""

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConfigError(
            "Missing API key. Set LLM_API_KEY in .env or in your shell environment."
        )

    model = args.model or os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
    if not model:
        raise ConfigError("Missing model. Set LLM_MODEL in .env or pass --model.")

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
        raise ConfigError("temperature must be between 0 and 2.")

    if max_tokens <= 0:
        raise ConfigError("max_tokens must be greater than 0.")

    base_url = args.base_url or os.getenv("LLM_BASE_URL") or None

    return LLMConfig(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=args.stream,
    )


def build_messages(user_text: str, system_prompt: str) -> list[dict[str, str]]:
    """Build the messages list sent to the model.

    In submodule 1, we only need system + user messages. Later, an agent loop
    will also add assistant messages and tool result messages.
    """

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]


def create_client(config: LLMConfig) -> Any:
    """Create the LLM client.

    The OpenAI SDK can also talk to many OpenAI-compatible providers when
    base_url is configured. This keeps the exercise flexible without changing
    the rest of the code.
    """

    if OpenAI is None:
        raise ConfigError("The openai package is not installed. Run: pip install openai")

    if config.base_url:
        return OpenAI(api_key=config.api_key, base_url=config.base_url)

    return OpenAI(api_key=config.api_key)


def ask_once(client: Any, config: LLMConfig, messages: list[dict[str, str]]) -> str:
    """Send one non-streaming chat request and return the assistant text."""

    response = client.chat.completions.create(
        model=config.model,
        messages=messages,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The model returned an empty response.")

    return content


def ask_stream(client: Any, config: LLMConfig, messages: list[dict[str, str]]) -> str:
    """Send one streaming chat request and print chunks as they arrive."""

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
    """Parse CLI arguments.

    The question is positional but optional, so you can either pass it directly
    or type it after the program starts.
    """

    parser = argparse.ArgumentParser(description="Ask one question to an LLM.")
    parser.add_argument("question", nargs="*", help="Question to send to the model.")
    parser.add_argument("--model", help="Override LLM_MODEL for this run.")
    parser.add_argument("--base-url", help="Override LLM_BASE_URL for this run.")
    parser.add_argument(
        "--temperature",
        type=float,
        help="Sampling temperature. Lower is more stable, higher is more creative.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        help="Maximum number of output tokens.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print the answer token by token as the model generates it.",
    )
    parser.add_argument(
        "--system-prompt",
        default=DEFAULT_SYSTEM_PROMPT,
        help="Override the default technical-teacher system prompt.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to the env file. Defaults to .env in the current directory.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug logs. The API key is never logged.",
    )
    return parser.parse_args(argv)


def get_question(args: argparse.Namespace) -> str:
    """Get the user question from CLI args or interactive input."""

    if args.question:
        return " ".join(args.question).strip()

    return input("请输入你的问题：").strip()


def main(argv: list[str] | None = None) -> int:
    """Program entry point.

    Returning an exit code instead of calling sys.exit everywhere makes the
    function easier to test later with pytest.
    """

    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(name)s - %(message)s",
    )

    try:
        load_dotenv(Path(args.env_file))
        config = build_config(args)
        question = get_question(args)

        if not question:
            raise ConfigError("Question cannot be empty.")

        messages = build_messages(question, args.system_prompt)

        LOGGER.debug("Using model=%s stream=%s", config.model, config.stream)
        LOGGER.debug("Messages count=%d", len(messages))

        client = create_client(config)

        if config.stream:
            ask_stream(client, config, messages)
        else:
            answer = ask_once(client, config, messages)
            print(answer)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        return 130
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # The first exercise keeps runtime errors readable.
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1


# Practice tasks for you:
# 1. Add a --save option that writes the final answer to a Markdown file.
# 2. Add a --repeat N option to ask the same question multiple times and compare
#    how temperature changes answer stability.
# 3. Add a simple conversation mode that keeps previous assistant replies in
#    messages until the user types "exit".
# 4. Log request latency without logging the API key or the full user message.


if __name__ == "__main__":
    raise SystemExit(main())
