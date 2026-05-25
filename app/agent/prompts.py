from app.tools.registry import ToolRegistry


SYSTEM_PROMPT = """你是一个最小工具型 Agent。
你可以根据用户问题选择工具，也可以直接回答。
当问题需要计算、文件搜索、网页摘要或待办管理时，优先使用对应工具。
"""


def build_tool_prompt(tool_registry: ToolRegistry) -> str:
    """构造工具说明文本。

    当前 mock Agent 没有真正把 prompt 发给 LLM，但保留这个函数是为了让工程结构贴近真实 Agent。
    TODO 练习 4：
    尝试把工具 schema 格式化为更适合 LLM 阅读的文本。
    """
    lines = [SYSTEM_PROMPT.strip(), "", "可用工具："]
    for tool in tool_registry.list_tools():
        lines.append(f"- {tool.name}: {tool.description}")
    return "\n".join(lines)

