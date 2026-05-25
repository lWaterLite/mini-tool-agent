from dataclasses import dataclass

from fastapi import Request

from app.agent.loop import AgentService
from app.core.config import Settings
from app.tools.calculator import CalculatorTool
from app.tools.file_search import FileSearchTool
from app.tools.registry import ToolRegistry
from app.tools.todo import TodoTool, TodoStore
from app.tools.web_summary_mock import WebSummaryMockTool


@dataclass(frozen=True)
class AppState:
    """应用级状态容器。

    练习重点：
    - settings 是只读配置。
    - tools 是工具注册表。
    - agent 是核心业务对象。
    - todo_store 是有状态组件，用来观察服务化后的共享状态问题。
    """

    settings: Settings
    tools: ToolRegistry
    agent: AgentService
    todo_store: TodoStore


def create_app_state(settings: Settings) -> AppState:
    """创建应用状态。

    TODO 练习 1：
    现在所有工具都在这里手动注册。你可以思考：
    - 如果未来工具越来越多，是否需要插件式自动注册？
    - 工具初始化失败时，应该让服务启动失败，还是只禁用该工具？
    """
    todo_store = TodoStore()
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(FileSearchTool(settings.file_search_root))
    registry.register(WebSummaryMockTool())
    registry.register(TodoTool(todo_store))

    agent = AgentService(tool_registry=registry, settings=settings)

    return AppState(
        settings=settings,
        tools=registry,
        agent=agent,
        todo_store=todo_store,
    )


def get_app_state(request: Request) -> AppState:
    """通过 FastAPI 依赖注入获取应用状态。"""
    return request.app.state.container

