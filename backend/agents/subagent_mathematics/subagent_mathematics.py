import logging

from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict, Annotated

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool

from core.config import settings

from agents.subagent_mathematics.tools import load_tools

logger = logging.getLogger(__name__)

# ---------- Global variable -------------

_subagent_mathematics = None

system_prompt = """
                You are a mathematics agent. You have access to a variety of tools that allow you to perform complex mathematical calculations and provide accurate results.
                Prefer using these tools to find the latest information needed to answer the user's query.
                """


# ---------- Define the subagent's internal workflow -------------
    
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def get_mathematics_workflow():
    '''
    Get the mathematics subagent workflow instance
    '''
    global _subagent_mathematics
    if _subagent_mathematics is None:
        _subagent_mathematics, n_tools = await build_mathematics_workflow()

        logger.info(f"Mathematics subagent loaded with {n_tools} tools")
    return _subagent_mathematics


async def build_mathematics_workflow():
    '''
    Build the mathematics subagent as a graph workflow.
    Returns:
        - The compiled graph workflow representing the subagent's internal logic
        - The number of tools available to the subagent
    '''

    tools = load_tools()

    llm = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_deployment,
        api_key=settings.azure_openai_api_key.get_secret_value(),
        api_version=settings.api_version,
        temperature=0,
    )
    llm_with_tools = llm.bind_tools(tools)


    workflow = StateGraph(State)

    async def llm_node(state: State):
        response = await llm_with_tools.ainvoke([SystemMessage(content=system_prompt)] + state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    workflow.add_node("llm_node", llm_node)
    workflow.add_node("tool_node", tool_node)

    workflow.add_edge(START, "llm_node")
    workflow.add_conditional_edges("llm_node",
        tools_condition,
        {
            "tools": "tool_node",
            "__end__": END
        }
    )

    workflow.add_edge("tool_node", "llm_node")

    return workflow.compile() , len(tools)

# ------------------- Define the subagent as a tool -------------------

@tool("mathematics_sub_agent")
async def agent(query: str) -> str:
    """This agent performs  mathematical calculations"""
    try:
        logger.info(f"Received query: {query}")

        workflow = await get_mathematics_workflow()
        result = await workflow.ainvoke({"messages": [HumanMessage(content=query)]})
        
        logger.info("Completed")

        return result["messages"][-1].content
    
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
        raise

