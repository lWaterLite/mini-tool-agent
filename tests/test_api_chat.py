from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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

