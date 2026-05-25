from enum import StrEnum
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.trace import new_trace_id


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    AGENT_ERROR = "AGENT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """应用内可预期错误。

    业务代码抛出 AppError，API 层统一转换成标准 JSON 错误响应。
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        trace_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.trace_id = trace_id
        self.details = details or {}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """统一处理应用内错误。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "trace_id": exc.trace_id,
            }
        },
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """把 FastAPI/Pydantic 校验错误也包装成统一格式。"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": ErrorCode.INVALID_REQUEST,
                "message": "请求参数校验失败",
                "trace_id": None,
                "details": exc.errors(),
            }
        },
    )


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理。

    TODO 练习 3：
    当前这里没有记录异常日志。请尝试接入 logger.exception，
    但注意不要把完整异常栈直接返回给 API 调用方。
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "服务内部错误",
                "trace_id": new_trace_id(),
            }
        },
    )
