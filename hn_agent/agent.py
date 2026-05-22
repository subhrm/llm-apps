"""
Agent workflow definition for the Hacker News Agent.
Constructs a ReAct agent using LangGraph and ChatOpenAI.
"""

from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from hn_agent import config
from hn_agent.tools import TOOLS

# Define the state shape
class AgentState(TypedDict):
    """State for the Hacker News summary agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]


# Initialize the LLM with config values
llm_kwargs = {
    "model": config.OPENAI_MODEL,
    "temperature": config.OPENAI_TEMPERATURE,
    "api_key": config.OPENAI_API_KEY,
}
if config.OPENAI_BASE_URL:
    llm_kwargs["base_url"] = config.OPENAI_BASE_URL

# Create the ChatOpenAI client
llm = ChatOpenAI(**llm_kwargs)

# Bind the Hacker News MCP tools to the model
llm_with_tools = llm.bind_tools(TOOLS)


async def call_model(state: AgentState) -> dict:
    """Invokes the LLM to decide on the next action or final answer."""
    messages = state["messages"]
    
    # Ensure system instructions are present at the beginning of the conversation
    system_prompt = (
        "You are an expert Hacker News summary assistant.\n"
        "Your task is to help users list, read, fetch, and summarize stories on Hacker News.\n"
        "Use the tools provided to fetch top stories, story details, and body content of linked articles.\n"
        "When summarizing multiple stories, present a structured, clean markdown list.\n"
        "Be concise, readable, and highly informative in your responses."
    )
    
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [SystemMessage(content=system_prompt)] + list(messages)
        
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


# Build the state graph
workflow = StateGraph(AgentState)

# Add node for LLM calls
workflow.add_node("agent", call_model)

# Add node for tool executions
workflow.add_node("tools", ToolNode(TOOLS))

# Connect nodes
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    tools_condition,
)
workflow.add_edge("tools", "agent")

# Compile the workflow
agent_app = workflow.compile()
