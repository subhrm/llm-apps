"""
LangChain tools wrapping the Hacker News MCP server over SSE.
Employs a ContextVar to securely share the active MCP ClientSession.
"""

from contextvars import ContextVar
from typing import Optional
from langchain_core.tools import tool
from mcp import ClientSession

# ContextVar to hold the active ClientSession for the duration of a run
mcp_session_var: ContextVar[Optional[ClientSession]] = ContextVar("mcp_session", default=None)


@tool
async def list_top_stories(limit: int = 30) -> str:
    """
    List the current top Hacker News stories from the front page.
    Args:
        limit (int): The maximum number of stories to fetch (default: 30, max: 50).
    Returns:
        str: A JSON string representation of the stories containing details like ID, title, score, comments count, etc.
    """
    session = mcp_session_var.get()
    if session is None:
        return "Error: MCP session is not active or initialized."
    try:
        import json
        result = await session.call_tool("list_top_stories", {"limit": limit})
        stories = []
        for block in result.content:
            if hasattr(block, "text") and block.text:
                try:
                    stories.append(json.loads(block.text))
                except json.JSONDecodeError:
                    # In case a block is raw text, add it as is
                    stories.append(block.text)
        return json.dumps(stories)
    except Exception as e:
        return f"Error calling list_top_stories: {e}"


@tool
async def get_story_details(story_id: int, max_comments: int = 5) -> str:
    """
    Fetch the details of a specific Hacker News story, including metadata and top comments.
    Args:
        story_id (int): The Hacker News story ID.
        max_comments (int): The maximum number of top-level comments to include (default: 5, max: 20).
    Returns:
        str: A markdown representation of the story metadata and comments.
    """
    session = mcp_session_var.get()
    if session is None:
        return "Error: MCP session is not active or initialized."
    try:
        result = await session.call_tool(
            "get_story_details", 
            {"story_id": story_id, "max_comments": max_comments}
        )
        return "".join(block.text for block in result.content if hasattr(block, "text"))
    except Exception as e:
        return f"Error calling get_story_details: {e}"


@tool
async def fetch_article_content(url: str) -> str:
    """
    Fetch and extract the readable main-body text of any URL/article linked in Hacker News stories.
    All boilerplate elements like headers, footers, scripts, and navigation will be stripped.
    Args:
        url (str): The article URL to fetch.
    Returns:
        str: The extracted plain text content optimized for LLM reading.
    """
    session = mcp_session_var.get()
    if session is None:
        return "Error: MCP session is not active or initialized."
    try:
        result = await session.call_tool("fetch_article_content", {"url": url})
        return "".join(block.text for block in result.content if hasattr(block, "text"))
    except Exception as e:
        return f"Error calling fetch_article_content: {e}"


# List of tools to export
TOOLS = [list_top_stories, get_story_details, fetch_article_content]
