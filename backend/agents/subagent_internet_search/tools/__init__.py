import importlib
import pkgutil
from pathlib import Path

from langchain_core.tools import BaseTool

_TOOLS_PATH = str(Path(__file__).parent)


def load_tools() -> list:
    """Discover and load all BaseTool instances from this package."""
    found_tools = []
    for _importer, module_name, _ispkg in pkgutil.iter_modules([_TOOLS_PATH]):
        module = importlib.import_module(f"{__package__}.{module_name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, BaseTool):
                found_tools.append(attr)
    return found_tools
