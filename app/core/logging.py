import logging
import json
from typing import Any

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


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """输出结构化日志事件。

    当前实现使用标准库 logging，不额外引入依赖。
    日志正文是 JSON 字符串，后续接入日志平台时更容易筛选 trace_id、tool_name 等字段。
    """
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def summarize_text(text: str, max_length: int = 80) -> str:
    """生成适合进入日志的文本摘要，避免把完整用户输入写入日志。"""
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length]}..."
