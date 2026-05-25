import json

from app.tools.registry import ToolRegistry


SYSTEM_PROMPT = """你是一个最小工具型 Agent。
你可以根据用户问题选择工具，也可以直接回答。
当问题需要计算、文件搜索、网页摘要或待办管理时，优先使用对应工具。
"""


def build_tool_prompt(tool_registry: ToolRegistry) -> str:
    """构造工具说明文本。

    当前 mock Agent 没有真正把 prompt 发给 LLM，但这个函数已经按真实 LLM 可读格式组织：
    每个工具包含用途、调用名和参数 JSON Schema。
    """
    lines = [
        SYSTEM_PROMPT.strip(),
        "",
        "你可以使用下列工具。需要工具时，请只选择其中一个工具名称，并生成符合 schema 的参数。",
        "",
    ]
    for index, tool in enumerate(tool_registry.list_tools(), start=1):
        schema = json.dumps(tool.parameters_schema(), ensure_ascii=False, indent=2)
        lines.extend(
            [
                f"{index}. 工具名称：{tool.name}",
                f"   工具用途：{tool.description}",
                "   参数 schema：",
                _indent(schema, spaces=3),
                "",
            ]
        )
    return "\n".join(lines)


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())
