import asyncio
from pathlib import Path

from app.tools.file_search import FileSearchTool


def test_file_search_finds_keyword() -> None:
    search_root = Path("tests/fixtures/search_root")

    tool = FileSearchTool(search_root)
    result = asyncio.run(tool.arun({"query": "服务化", "max_results": 3}, trace_id="trace_test"))

    assert "sample.md" in result.output
    assert result.data["matches"][0]["line"] == 2
