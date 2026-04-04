import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

from agents.subagent_internet_search import subagent_internet_search
from agents.subagent_mathematics import subagent_mathematics

from core.config import settings

# Global Variables

logger = logging.getLogger(__name__)

from datetime import date

_master = None
system_prompt = f"""
                You are an orchestration agent that orchestrates multiple subagents to complete tasks.
                Never answer the user's query directly. Instead, you must delegate to the appropriate subagent(s).
                Think carefully before you delegate to the sub agent.

                Must Instructions:
                1. Never refer to old conversation history when answering a query. Always answer based on the current query and the information retrieved by the subagents.
                2. Pass the user's query exactly as-is to the subagent. Do NOT modify, rephrase, or add any date/year context to it.
                3. If you are unsure which agent to delegate. Pick the internet search agent as the fallback.
                
                Always prefer using the subagents to answer the user's query, and only answer directly if the query cannot be handled by any of the subagents.
                """

# Create the master agent and include the subagent as one of its tools

async def get_master_agent():
    global _master
    if _master is None:
        llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_deployment,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            api_version=settings.api_version,
            temperature=0,
        )
        _master = create_agent(
            model=llm,
            tools=[subagent_internet_search.agent, subagent_mathematics.agent],
            checkpointer=InMemorySaver(),
            system_prompt=system_prompt
        )
        logger.info("Master agent loaded with subagents as tools")

        png_data = _master.get_graph(xray=True).draw_mermaid_png()
        output_path = Path(__file__).resolve().parent.parent / "master.png"
        output_path.write_bytes(png_data)
        logger.info(f"Graph saved to {output_path}")
    return _master

async def invoke_master_agent(query: str, thread_id: str = "default") -> str:
    """Run the master agent with the given query."""

    logger.info(f"Received query: {query}")

    config = {"configurable": {"thread_id": thread_id}}

    master = await get_master_agent()
    result = await master.ainvoke({"messages": [HumanMessage(content=query)]}, config=config)

    logger.info("Master agent completed")

    return result["messages"][-1].content


async def stream_master_agent(query: str, thread_id: str = "default"):
    """Stream tokens from the master agent's final response."""

    logger.info(f"Streaming query: {query}")

    config = {"configurable": {"thread_id": thread_id}}

    master = await get_master_agent()

    async for event in master.astream_events(
        {"messages": [HumanMessage(content=query)]},
        config=config,
        version="v2",
    ):
        kind = event.get("event")

        # Stream only LLM token chunks that carry text content.
        # Tool-calling steps emit empty content (only tool_call_chunks),
        # so this naturally filters to the final response.
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                # Skip chunks that are part of a tool-calling turn
                if getattr(chunk, "tool_call_chunks", None):
                    continue
                yield chunk.content
                await asyncio.sleep(0.05)   # Smooth out the streaming

    logger.info("Streaming completed")



