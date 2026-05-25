import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
            max_file_search_results=int(os.getenv("MAX_FILE_SEARCH_RESULTS", "5")),
            max_agent_steps=int(os.getenv("MAX_AGENT_STEPS", "4")),
        )
