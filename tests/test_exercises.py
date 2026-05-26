import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# @pytest.mark.skip(reason="练习题：实现 streaming 错误事件后，再取消跳过并补充断言。")
def test_stream_returns_error_event_when_tool_fails() -> None:
    """练习 1：让 /chat/stream 在工具失败时返回 event: error。

    建议你构造一个会触发工具错误的请求，例如除以 0。
    断言方向：
    - 响应状态码仍然是 200，因为 SSE 连接已经建立。
    - 响应体中包含 event: error。
    - error data 中包含 code、message、trace_id。
    """

    with client.stream("POST", "/chat/stream", json={"message": "计算 1 / 0"}) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: error" in body

    event_blocks = iter(event_block for event_block in body.split("\n\n"))
    while True:
        event_block = next(event_blocks, None)
        if event_block.startswith("event: error"):
            payload = json.loads(event_block.removeprefix("event: error\ndata: "))
            assert payload["event"] == "error"
            assert payload["trace_id"].startswith("trace_")
            assert payload["data"]["code"] == "TOOL_EXECUTION_ERROR"
            assert payload["data"]["message"] == "除数不能为 0"
        if not event_block:
            break


@pytest.mark.skip(reason="练习题：实现工具超时配置后，再取消跳过并补充断言。")
def test_exercise_agent_converts_tool_timeout_to_app_error() -> None:
    """练习 2：为工具执行增加超时保护。

    建议你写一个测试专用慢工具，arun 中 await asyncio.sleep。
    断言方向：
    - AgentService 应该抛出 AppError。
    - 错误码可以是 TOOL_EXECUTION_ERROR。
    - 错误消息中应该能看出是工具超时。
    """


@pytest.mark.skip(reason="练习题：实现真实 LLM planner 的 mock 测试后，再取消跳过并补充断言。")
def test_exercise_llm_planner_uses_mock_model_output() -> None:
    """练习 3：为真实 LLM planner 写 mock 测试。

    注意测试不要调用真实 LLM。
    断言方向：
    - mock 模型返回固定 JSON。
    - planner 能解析出工具名称和参数。
    - 字段缺失时能给出清晰错误。
    """
