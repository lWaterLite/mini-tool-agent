from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


client = TestClient(create_app(Settings(agent_planner_mode="mock")))


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tools() -> None:
    response = client.get("/tools")

    assert response.status_code == 200
    tool_names = {tool["name"] for tool in response.json()["tools"]}
    assert {"calculator", "file_search", "web_summary_mock", "todo"} <= tool_names


def test_chat_without_tool() -> None:
    response = client.post("/chat", json={"message": "你好"})

    assert response.status_code == 200
    body = response.json()
    assert body["used_tools"] == []
    assert body["trace_id"].startswith("trace_")


def test_chat_with_calculator() -> None:
    response = client.post("/chat", json={"message": "计算 3 * (4 + 5)"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "计算结果：27.0"
    assert body["used_tools"] == ["calculator"]
    assert body["tool_calls"][0]["name"] == "calculator"


def test_chat_with_todo_uses_session_id() -> None:
    add_response = client.post(
        "/chat",
        json={"message": "添加待办 学习 mock", "session_id": "api_student"},
    )
    list_response = client.post(
        "/chat",
        json={"message": "查看待办", "session_id": "api_student"},
    )

    assert add_response.status_code == 200
    assert list_response.status_code == 200
    assert "学习 mock" in list_response.json()["answer"]


def test_chat_rejects_invalid_max_steps_type() -> None:
    response = client.post("/chat", json={"message": "你好", "max_steps": "很多步"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_chat_rejects_too_small_max_steps() -> None:
    response = client.post("/chat", json={"message": "计算 1 + 2 并查看待办", "max_steps": 1})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_chat_validation_error() -> None:
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_chat_stream() -> None:
    with client.stream("POST", "/chat/stream", json={"message": "计算 1 + 2"}) as response:
        assert response.status_code == 200
        body = response.read().decode("utf-8")

    assert "event: start" in body
    assert "event: tool_call" in body
    assert "event: final" in body
