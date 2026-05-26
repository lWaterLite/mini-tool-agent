import pytest

from app.core.errors import AppError
from app.tools.web_summary_mock import WebSummaryMockTool


@pytest.mark.asyncio
async def test_web_summary_mock_returns_stable_summary() -> None:
    tool = WebSummaryMockTool()

    result = await tool.arun({"url": "https://example.com/article"}, trace_id="trace_test")

    assert "https://example.com/article" in result.output
    assert result.data["mock"] is True


@pytest.mark.asyncio
async def test_web_summary_mock_rejects_invalid_url() -> None:
    tool = WebSummaryMockTool()

    with pytest.raises(AppError) as exc_info:
        await tool.arun({"url": "not-a-url"}, trace_id="trace_test")

    assert exc_info.value.code == "INVALID_REQUEST"

