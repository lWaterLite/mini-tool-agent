from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from app.agent.loop import AgentService
from app.core.config import Settings
from app.tools.base import BaseTool
from app.tools.calculator import CalculatorTool
from app.tools.file_search import FileSearchTool
from app.tools.registry import ToolRegistry
from app.tools.todo import TodoTool, TodoStore
from app.tools.web_summary_mock import WebSummaryMockTool

ToolFactory = Callable[[Settings, TodoStore], BaseTool]


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

    工具注册集中在一个可扩展的工厂列表中。
    这种写法比在函数里一行行散落注册更容易维护：新增工具时只需要增加一个工厂。
    """
    todo_store = TodoStore()
    registry = build_tool_registry(settings, todo_store)

    agent = AgentService(tool_registry=registry, settings=settings)

    return AppState(
        settings=settings,
        tools=registry,
        agent=agent,
        todo_store=todo_store,
    )


def build_tool_registry(settings: Settings, todo_store: TodoStore) -> ToolRegistry:
    """构建工具注册表。

    当前仍然是显式工厂列表，而不是动态扫描模块。
    对学习项目来说，显式列表更容易阅读；对大型项目，可以进一步演进为插件发现机制。
    """
    registry = ToolRegistry()
    for tool_factory in default_tool_factories():
        tool = tool_factory(settings, todo_store)
        registry.register(tool)
    return registry


def default_tool_factories() -> list[ToolFactory]:
    """返回默认工具工厂列表。

    工厂函数接收配置和共享状态，因此工具既可以是无状态工具，也可以是有状态工具。
    """
    return [
        lambda _settings, _todo_store: CalculatorTool(),
        lambda settings, _todo_store: FileSearchTool(settings.file_search_root),
        lambda _settings, _todo_store: WebSummaryMockTool(),
        lambda _settings, todo_store: TodoTool(todo_store),
    ]


def get_app_state(request: Request) -> AppState:
    """通过 FastAPI 依赖注入获取应用状态。"""
    return request.app.state.container
