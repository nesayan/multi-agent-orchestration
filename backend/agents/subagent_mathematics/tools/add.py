
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool


@tool("addition_tool")
def addition_tool(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b