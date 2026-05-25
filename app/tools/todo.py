import asyncio
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.tools.base import BaseTool, ToolResult

DEFAULT_SESSION_ID = "default"


class TodoArgs(BaseModel):
    action: Literal["add", "list", "done"] = Field(description="待办操作类型")
    content: str | None = Field(default=None, max_length=200, description="新增待办内容")
    item_id: str | None = Field(default=None, max_length=80, description="要完成的待办 ID")
    session_id: str | None = Field(default=None, max_length=80, description="用于隔离待办列表的会话 ID")

    @model_validator(mode="after")
    def validate_cross_fields(self) -> "TodoArgs":
        if self.action == "add" and not self.content:
            raise ValueError("添加待办时必须提供 content")
        if self.action == "done" and not self.item_id:
            raise ValueError("完成待办时必须提供 item_id")
        return self


@dataclass
class TodoItem:
    id: str
    content: str
    done: bool = False


@dataclass
class TodoStore:
    """内存待办存储。

    按 session_id 隔离待办列表，避免多个用户共享同一份内存状态。
    这仍然不是持久化存储：服务重启后数据会丢失。
    """

    items_by_session: dict[str, list[TodoItem]] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def add(self, content: str, session_id: str) -> TodoItem:
        async with self.lock:
            item = TodoItem(id=f"todo_{uuid4().hex[:8]}", content=content)
            self.items_by_session.setdefault(session_id, []).append(item)
            return item

    async def list_items(self, session_id: str) -> list[TodoItem]:
        async with self.lock:
            return list(self.items_by_session.get(session_id, []))

    async def mark_done(self, item_id: str, session_id: str) -> TodoItem | None:
        async with self.lock:
            for item in self.items_by_session.get(session_id, []):
                if item.id == item_id:
                    item.done = True
                    return item
        return None


class TodoTool(BaseTool):
    name = "todo"
    description = "管理内存中的待办事项，支持 add、list 和 done。"
    args_model = TodoArgs

    def __init__(self, store: TodoStore) -> None:
        self._store = store

    async def arun(self, arguments: dict[str, object], trace_id: str) -> ToolResult:
        args = self.validate_arguments(arguments, trace_id)
        assert isinstance(args, TodoArgs)
        session_id = args.session_id or DEFAULT_SESSION_ID

        if args.action == "add":
            assert args.content is not None
            item = await self._store.add(args.content, session_id)
            return ToolResult(output=f"已添加待办：{item.content}", data={"item": item.__dict__, "session_id": session_id})

        if args.action == "list":
            items = await self._store.list_items(session_id)
            if not items:
                return ToolResult(output="当前没有待办事项。", data={"items": [], "session_id": session_id})
            lines = [f"{item.id} [{'x' if item.done else ' '}] {item.content}" for item in items]
            return ToolResult(output="\n".join(lines), data={"items": [item.__dict__ for item in items], "session_id": session_id})

        assert args.item_id is not None
        item = await self._store.mark_done(args.item_id, session_id)
        if item is None:
            return ToolResult(output=f"没有找到待办：{args.item_id}", data={"item": None, "session_id": session_id})
        return ToolResult(output=f"已完成待办：{item.content}", data={"item": item.__dict__, "session_id": session_id})
