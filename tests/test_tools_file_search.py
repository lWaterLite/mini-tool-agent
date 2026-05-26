import asyncio
from pathlib import Path

import pytest

from app.core.errors import AppError
from app.tools.file_search import FileSearchTool


def test_file_search_finds_keyword() -> None:
    search_root = Path("tests/fixtures/search_root")

    tool = FileSearchTool(search_root)
    result = asyncio.run(tool.arun({"query": "服务化", "max_results": 3}, trace_id="trace_test"))

    assert "sample.md" in result.output
    assert result.data["matches"][0]["line"] == 2


def test_file_search_returns_empty_result_when_keyword_missing() -> None:
    search_root = Path("tests/fixtures/search_root")

    tool = FileSearchTool(search_root)
    result = asyncio.run(tool.arun({"query": "不存在的关键词", "max_results": 3}, trace_id="trace_test"))

    assert result.output == "没有找到匹配内容。"
    assert result.data["matches"] == []


def test_file_search_rejects_missing_root() -> None:
    tool = FileSearchTool(Path("tests/fixtures/not_exists"))

    with pytest.raises(AppError) as exc_info:
        asyncio.run(tool.arun({"query": "Agent", "max_results": 3}, trace_id="trace_test"))

    assert exc_info.value.code == "TOOL_EXECUTION_ERROR"
