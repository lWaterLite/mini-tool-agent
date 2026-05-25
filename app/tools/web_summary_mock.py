from pydantic import BaseModel, Field, HttpUrl

from app.tools.base import BaseTool, ToolResult


class WebSummaryArgs(BaseModel):
    url: HttpUrl = Field(description="要摘要的网页 URL")


class WebSummaryMockTool(BaseTool):
    name = "web_summary_mock"
    description = "模拟网页摘要工具，不访问真实网络，用于稳定测试 Agent 流程。"
    args_model = WebSummaryArgs

    async def arun(self, arguments: dict[str, object], trace_id: str) -> ToolResult:
        args = self.validate_arguments(arguments, trace_id)
        assert isinstance(args, WebSummaryArgs)

        url = str(args.url)
        summary = f"这是对 {url} 的模拟摘要。真实项目中这里可以替换为网页抓取和总结流程。"
        return ToolResult(output=summary, data={"url": url, "mock": True})

