import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.errors import AppError, ErrorCode
from app.tools.base import BaseTool, ToolResult


class FileSearchArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=120, description="要搜索的关键词")
    max_results: int = Field(default=5, ge=1, le=20, description="最多返回多少条结果")


class FileSearchTool(BaseTool):
    name = "file_search"
    description = "在指定项目目录中搜索包含关键词的文本文件。"
    args_model = FileSearchArgs

    def __init__(self, root: Path) -> None:
        self._root = root

    async def arun(self, arguments: dict[str, object], trace_id: str) -> ToolResult:
        args = self.validate_arguments(arguments, trace_id)
        assert isinstance(args, FileSearchArgs)

        matches = await asyncio.to_thread(self._search, args.query, args.max_results, trace_id)
        if not matches:
            return ToolResult(output="没有找到匹配内容。", data={"matches": []})

        output = "\n".join(f"{item['path']}:{item['line']} {item['text']}" for item in matches)
        return ToolResult(output=output, data={"matches": matches})

    def _search(self, query: str, max_results: int, trace_id: str) -> list[dict[str, object]]:
        root = self._root.resolve()
        if not root.exists():
            raise AppError(ErrorCode.TOOL_EXECUTION_ERROR, f"搜索根目录不存在：{self._root}", trace_id=trace_id)

        matches: list[dict[str, object]] = []
        for path in root.rglob("*"):
            if len(matches) >= max_results:
                break
            if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".py"}:
                continue

            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue

            for line_no, text in enumerate(lines, start=1):
                if query.lower() in text.lower():
                    matches.append(
                        {
                            "path": str(path.relative_to(root)),
                            "line": line_no,
                            "text": text.strip(),
                        }
                    )
                    break

        return matches

