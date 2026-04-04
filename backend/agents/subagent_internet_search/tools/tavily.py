from langchain_tavily import TavilySearch

from core.config import settings


tavily_tool = TavilySearch(
    max_results=5,
    tavily_api_key=settings.tavily_api_key.get_secret_value(),
)

