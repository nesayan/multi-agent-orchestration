
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool


@tool("multiplication_tool")
def multiplication_tool(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b