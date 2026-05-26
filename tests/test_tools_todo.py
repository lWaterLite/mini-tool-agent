import pytest

from app.core.errors import AppError
from app.tools.todo import TodoStore, TodoTool


@pytest.mark.asyncio
async def test_todo_add_and_list_items_in_same_session() -> None:
    tool = TodoTool(TodoStore())

    add_result = await tool.arun(
        {"action": "add", "content": "学习测试分层", "session_id": "student_a"},
        trace_id="trace_test",
    )
    list_result = await tool.arun(
        {"action": "list", "session_id": "student_a"},
        trace_id="trace_test",
    )

    assert add_result.data["session_id"] == "student_a"
    assert "学习测试分层" in list_result.output


@pytest.mark.asyncio
async def test_todo_mark_done_changes_item_status() -> None:
    tool = TodoTool(TodoStore())

    add_result = await tool.arun(
        {"action": "add", "content": "补充 API 测试", "session_id": "student_a"},
        trace_id="trace_test",
    )
    item_id = add_result.data["item"]["id"]
    done_result = await tool.arun(
        {"action": "done", "item_id": item_id, "session_id": "student_a"},
        trace_id="trace_test",
    )

    assert done_result.data["item"]["done"] is True
    assert done_result.output == "已完成待办：补充 API 测试"


@pytest.mark.asyncio
async def test_todo_list_is_empty_for_different_session() -> None:
    tool = TodoTool(TodoStore())

    await tool.arun(
        {"action": "add", "content": "只属于 A 的任务", "session_id": "student_a"},
        trace_id="trace_test",
    )
    result = await tool.arun(
        {"action": "list", "session_id": "student_b"},
        trace_id="trace_test",
    )

    assert result.output == "当前没有待办事项。"
    assert result.data["items"] == []


@pytest.mark.asyncio
async def test_todo_rejects_add_without_content() -> None:
    tool = TodoTool(TodoStore())

    with pytest.raises(AppError) as exc_info:
        await tool.arun({"action": "add", "session_id": "student_a"}, trace_id="trace_test")

    assert exc_info.value.code == "INVALID_REQUEST"

