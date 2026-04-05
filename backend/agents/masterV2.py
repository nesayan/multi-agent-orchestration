import sys
import asyncio
import logging
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from typing import Literal
from pydantic import BaseModel
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from typing_extensions import TypedDict, Annotated

from agents.subagent_internet_search.subagent_internet_search import get_internet_search_workflow
from agents.subagent_mathematics.subagent_mathematics import get_mathematics_workflow

from core.config import settings

# Global Variables

logger = logging.getLogger(__name__)

_master = None
system_prompt = """
                You are an orchestration agent that orchestrates multiple subagents to complete tasks.
                Think carefully before you delegate to the sub agent.

                Must Instructions:
                1. Never refer to old conversation history when answering a query. Always answer based on the current query and the information retrieved by the subagents.
                2. Pass the user's query exactly as-is to the subagent. Do NOT modify, rephrase, or add any date/year context to it.
                3. For simple conversational queries (greetings, small talk, thank you, etc.) that do not require any information retrieval or computation, choose FINISH immediately. Do NOT delegate to any subagent.
                4. Only use the internet search agent as a fallback when the query genuinely requires external information and no other subagent fits.
                5. Once a subagent has already returned results for the current query, you MUST choose FINISH to synthesize the response. Do NOT re-delegate to the same subagent.
                6. If the user's query is unclear, incomplete, or doesn't make sense, choose FINISH and ask the user to provide more details instead of delegating to a subagent.
                7. If the user's query is ambiguous (e.g. a common name, a broad topic with many possible meanings), choose FINISH and ask the user to clarify with more specific details rather than searching with insufficient context.
                
                Available subagents:
                - internet_search: Use this for general queries or to search for the latest information on any topic.
                - mathematics: Use this for mathematical calculations.
                - FINISH: Use this when the subagents have already gathered enough information and you are ready to provide the final response.
                """


class MasterState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next: str


class RouteDecision(BaseModel):
    next: Literal["internet_search", "mathematics", "FINISH"]

# Create the master agent with subagents as subgraph nodes

async def get_masterV2_agent():
    global _master
    if _master is None:
        llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_deployment,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            api_version=settings.api_version,
            temperature=0,
        )

        internet_wf = await get_internet_search_workflow()
        math_wf = await get_mathematics_workflow()

        routing_llm = llm.with_structured_output(RouteDecision)

        async def orchestrator(state: MasterState):
            decision = await routing_llm.ainvoke(
                [SystemMessage(content=system_prompt)] + state["messages"]
            )
            logger.info(f"Routing decision: {decision.next}")
            return {"next": decision.next}

        async def synthesizer(state: MasterState):
            response = await llm.ainvoke(
                [SystemMessage(content="Based on the conversation, provide a helpful final response to the user.")]
                + state["messages"]
            )
            return {"messages": [response]}

        graph = StateGraph(MasterState)

        graph.add_node("orchestrator", orchestrator)
        graph.add_node("internet_search", internet_wf)
        graph.add_node("mathematics", math_wf)
        graph.add_node("synthesizer", synthesizer)

        graph.add_edge(START, "orchestrator")
        graph.add_conditional_edges("orchestrator", lambda state: state["next"], {
            "internet_search": "internet_search",
            "mathematics": "mathematics",
            "FINISH": "synthesizer",
        })
        graph.add_edge("internet_search", "orchestrator")
        graph.add_edge("mathematics", "orchestrator")
        graph.add_edge("synthesizer", END)

        _master = graph.compile(checkpointer=InMemorySaver())
        _master.recursion_limit = settings.graph_recursion_limit

        logger.info(f"Master agent loaded with subgraphs (recursion_limit={settings.graph_recursion_limit})")

        png_data = _master.get_graph(xray=True).draw_mermaid_png()
        output_path = Path(__file__).resolve().parent.parent / "masterV2.png"
        with open(output_path, "wb") as f:
            f.write(png_data)
        logger.info(f"Graph saved to {output_path}")
    return _master

async def invoke_masterV2_agent(query: str, thread_id: str = "default") -> str:
    """Run the master agent with the given query."""

    logger.info(f"Received query: {query}")

    config = {"configurable": {"thread_id": thread_id}}

    master = await get_masterV2_agent()
    result = await master.ainvoke({"messages": [HumanMessage(content=query)]}, config=config)

    logger.info("Master agent completed")

    return result["messages"][-1].content


async def stream_masterV2_agent(query: str, thread_id: str = "default"):
    """Stream tokens from the master agent's synthesizer node."""

    logger.info(f"Streaming query: {query}")

    config = {"configurable": {"thread_id": thread_id}}

    master = await get_masterV2_agent()

    async for event in master.astream_events(
        {"messages": [HumanMessage(content=query)]},
        config=config,
        version="v2",
    ):
        kind = event.get("event")
        tags = event.get("tags", [])    # tags has values like ['seq:step:1']
        metadata = event.get("metadata", {})
        langgraph_node = metadata.get("langgraph_node", "") # The node name ie "orchestrator", "internet_search", "mathematics", "synthesizer"

        # Logs for debugging
        # logger.debug(f"Kind: {kind}\nTags: {tags}\nNode: {langgraph_node}\nContent: {getattr(event['data'], 'chunk', None)}")
        
        # Only yield tokens from the synthesizer node's LLM call
        if kind == "on_chat_model_stream" and langgraph_node == "synthesizer":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield chunk.content
                await asyncio.sleep(0.05)   # Smooth out the streaming

    logger.info("Streaming completed")
