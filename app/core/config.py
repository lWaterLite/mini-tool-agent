import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是整数，当前值为：{value}") from exc


def _float_from_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"环境变量 {name} 必须是数字，当前值为：{value}") from exc


@dataclass(frozen=True)
class Settings:
    """应用配置。

    这里没有引入 pydantic-settings，是为了让本练习少一个依赖。
    真实项目中，你可以考虑用 pydantic-settings 管理复杂配置。
    """

    app_name: str = "mini-tool-agent"
    environment: str = "development"
    debug: bool = True
    file_search_root: Path = Path("documents")
    log_level: str = "INFO"
    max_file_search_results: int = 5
    max_agent_steps: int = 4
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 800

    @classmethod
    def from_env(cls) -> "Settings":
        """从环境变量构建配置。"""
        # 先加载 .env，再读取 os.environ。真实环境中系统环境变量仍然可以覆盖 .env。
        load_dotenv()
        return cls(
            app_name=os.getenv("APP_NAME", "mini-tool-agent"),
            environment=os.getenv("APP_ENV", "development"),
            debug=_bool_from_env(os.getenv("APP_DEBUG"), True),
            file_search_root=Path(os.getenv("FILE_SEARCH_ROOT", "documents")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_file_search_results=_int_from_env("MAX_FILE_SEARCH_RESULTS", 5),
            max_agent_steps=_int_from_env("MAX_AGENT_STEPS", 4),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_base_url=os.getenv("LLM_BASE_URL") or None,
            llm_temperature=_float_from_env("LLM_TEMPERATURE", 0.3),
            llm_max_tokens=_int_from_env("LLM_MAX_TOKENS", 800),
        )
