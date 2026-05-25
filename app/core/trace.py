from uuid import uuid4


def new_trace_id() -> str:
    """生成一次请求的追踪 ID。"""
    return f"trace_{uuid4().hex[:12]}"

