import logging

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """配置基础日志格式。"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """统一获取 logger，方便后续替换日志实现。"""
    return logging.getLogger(name)

