from app.core.errors import AppError, ErrorCode
from app.tools.base import BaseTool


class ToolRegistry:
    """工具注册表。

    Agent 不直接 import 每一个工具，而是通过注册表按名称查找工具。
    这会让工具层更容易扩展，也让 /tools 接口可以直接复用注册表信息。
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具名称重复：{tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            raise AppError(ErrorCode.TOOL_NOT_FOUND, f"工具不存在：{name}")
        return tool

    def list_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

