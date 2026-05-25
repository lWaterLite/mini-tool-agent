from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.errors import AppError, ErrorCode


class ToolResult(BaseModel):
    output: str
    data: dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """工具基类。

    每个工具都需要提供：
    - name：给 Agent 调用的稳定名称。
    - description：给模型、API 和人类阅读的工具说明。
    - args_model：工具参数模型。
    - arun：异步执行入口。
    """

    name: str
    description: str
    args_model: type[BaseModel]

    def parameters_schema(self) -> dict[str, Any]:
        return self.args_model.model_json_schema()

    def validate_arguments(self, arguments: dict[str, Any], trace_id: str) -> BaseModel:
        try:
            return self.args_model.model_validate(arguments)
        except ValidationError as exc:
            raise AppError(
                ErrorCode.INVALID_REQUEST,
                f"工具 {self.name} 的参数校验失败",
                trace_id=trace_id,
                details={"errors": exc.errors()},
            ) from exc

    @abstractmethod
    async def arun(self, arguments: dict[str, Any], trace_id: str) -> ToolResult:
        """异步执行工具。"""

