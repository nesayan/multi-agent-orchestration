
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool


@tool("subtraction_tool")
def subtraction_tool(a: float, b: float) -> float:
    """Subtract two numbers."""
    return a - b