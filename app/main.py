from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.routes import router
from app.core.config import Settings
from app.core.errors import app_error_handler, unexpected_error_handler, validation_error_handler
from app.core.logging import configure_logging
from app.core.errors import AppError
from app.api.dependencies import create_app_state


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建 FastAPI 应用实例。

    这里采用工厂函数，而不是在模块顶层直接写死所有状态。
    这样测试时可以传入专用配置，未来也更容易为不同环境创建不同应用。
    """
    resolved_settings = settings or Settings.from_env()
    configure_logging(resolved_settings)

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        description="一个用于学习 LLM Agent 服务化、依赖注入、工具调用和 streaming 的练习工程。",
    )

    # 应用状态只在启动时创建一次，然后通过依赖注入传给路由函数。
    app.state.container = create_app_state(resolved_settings)

    app.include_router(router)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unexpected_error_handler)

    return app


app = create_app()

