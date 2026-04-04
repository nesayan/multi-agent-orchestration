
from langchain_core.tools.structured import StructuredTool
from langchain_core.tools import tool


@tool("division_tool")
def division_tool(a: float, b: float) -> float:
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b