from types import SimpleNamespace

import pytest

from app.agent.planners import LLMPlanner, RuleBasedPlanner, build_planner
from app.core.config import Settings
from app.core.errors import AppError
from app.tools.calculator import CalculatorTool
from app.tools.registry import ToolRegistry


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[dict] = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content),
                )
            ]
        )


class FakeChat:
    def __init__(self, content: str) -> None:
        self.completions = FakeCompletions(content)


class FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = FakeChat(content)


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(CalculatorTool())
    return registry


@pytest.mark.asyncio
async def test_llm_planner_returns_direct_answer_without_tools() -> None:
    client = FakeClient('{"tool_calls":[],"clarification":null,"direct_answer":"你好，我是真实 LLM 的直接回答。"}')
    settings = Settings(agent_planner_mode="llm", llm_api_key="test-key")
    planner = LLMPlanner(settings, build_registry(), client=client)

    plan = await planner.plan("你好", session_id=None)

    assert plan.tool_calls == []
    assert plan.direct_answer == "你好，我是真实 LLM 的直接回答。"


@pytest.mark.asyncio
async def test_rule_based_planner_keeps_mock_calculator_behavior() -> None:
    planner = RuleBasedPlanner(Settings())

    plan = await planner.plan("计算 2 + 3", session_id=None)

    assert plan.clarification is None
    assert plan.tool_calls[0].name == "calculator"
    assert plan.tool_calls[0].arguments == {"expression": "2 + 3"}


@pytest.mark.asyncio
async def test_llm_planner_uses_fake_client_without_network() -> None:
    client = FakeClient('{"tool_calls":[{"name":"calculator","arguments":{"expression":"1 + 2"}}],"clarification":null}')
    settings = Settings(agent_planner_mode="llm", llm_api_key="test-key", llm_model="test-model")
    planner = LLMPlanner(settings, build_registry(), client=client)

    plan = await planner.plan("帮我计算 1 + 2", session_id="student")

    assert plan.clarification is None
    assert plan.tool_calls[0].name == "calculator"
    assert plan.tool_calls[0].arguments == {"expression": "1 + 2"}
    assert client.chat.completions.requests[0]["model"] == "test-model"


@pytest.mark.asyncio
async def test_llm_planner_accepts_json_code_block() -> None:
    client = FakeClient(
        '```json\n{"tool_calls":[{"name":"calculator","arguments":{"expression":"3 + 4"}}],"clarification":null}\n```'
    )
    planner = LLMPlanner(Settings(agent_planner_mode="llm", llm_api_key="test-key"), build_registry(), client=client)

    plan = await planner.plan("计算 3 + 4", session_id=None)

    assert plan.tool_calls[0].arguments == {"expression": "3 + 4"}


@pytest.mark.asyncio
async def test_llm_planner_rejects_unknown_tool() -> None:
    client = FakeClient('{"tool_calls":[{"name":"unknown","arguments":{}}],"clarification":null}')
    planner = LLMPlanner(Settings(agent_planner_mode="llm", llm_api_key="test-key"), build_registry(), client=client)

    with pytest.raises(AppError, match="未知工具"):
        await planner.plan("调用未知工具", session_id=None)


def test_build_planner_uses_mock_by_default() -> None:
    planner = build_planner(Settings(), build_registry())

    assert isinstance(planner, RuleBasedPlanner)


def test_build_planner_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="AGENT_PLANNER_MODE"):
        build_planner(Settings(agent_planner_mode="invalid"), build_registry())


@pytest.mark.asyncio
async def test_llm_planner_requires_api_key_when_creating_real_client() -> None:
    planner = LLMPlanner(Settings(agent_planner_mode="llm", llm_api_key=None), build_registry())

    with pytest.raises(AppError, match="LLM_API_KEY"):
        await planner.plan("你好", session_id=None)
