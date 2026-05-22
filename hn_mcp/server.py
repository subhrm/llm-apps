"""
Hacker News MCP server module.
Exposes Hacker News tools and integrates with the FastMCP SSE application wrapper.
"""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette

from hn_mcp.hn_client import HackerNewsClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hn_mcp.server")

# Initialize FastMCP server
mcp = FastMCP("HackerNews")

# Initialize Hacker News client
hn_client = HackerNewsClient()


@mcp.tool()
async def list_top_stories(limit: int = 30) -> list:
    """
    Lists the current top stories from the Hacker News homepage.

    Args:
        limit (int): The number of stories to fetch (default: 30, maximum: 50).
    """
    # Cap limit to reasonable range
    limit = max(1, min(limit, 50))
    
    try:
        logger.info(f"Tool list_top_stories called with limit={limit}")
        return await hn_client.fetch_top_stories(limit=limit)
    except Exception as e:
        logger.exception("Error in list_top_stories tool")
        raise RuntimeError(f"Failed to fetch top stories: {str(e)}")


@mcp.tool()
async def get_story_details(story_id: int, max_comments: int = 5) -> str:
    """
    Gets details of a specific Hacker News story including its source URL and top comments.

    Args:
        story_id (int): The ID of the Hacker News story.
        max_comments (int): The maximum number of top-level comments to fetch (default: 5, maximum: 20).
    """
    max_comments = max(0, min(max_comments, 20))
    
    try:
        logger.info(f"Tool get_story_details called for ID {story_id} with max_comments={max_comments}")
        details = await hn_client.fetch_story_details(story_id, max_comments=max_comments)
        
        lines = [
            f"# {details['title']}",
            f"- **Author:** `{details['by']}`",
            f"- **Score:** `{details['score']} points`",
            f"- **HN Link:** {details['hn_url']}",
            f"- **Source URL:** {details['url']}",
            f"- **Total Comments:** `{details['descendants']}`",
            f"- **Published:** *{details['time']}*\n",
        ]
        
        if max_comments > 0:
            lines.append(f"## Top {len(details['comments'])} Comments")
            if not details["comments"]:
                lines.append("No comments available.")
            else:
                for comment in details["comments"]:
                    lines.append(
                        f"---\n"
                        f"**Comment by {comment['by']}** (on {comment['time']}):\n\n"
                        f"{comment['text']}\n"
                    )
                    
        return "\n".join(lines)
        
    except Exception as e:
        logger.exception(f"Error in get_story_details tool for story {story_id}")
        return f"Error: Failed to fetch story details for ID {story_id}: {str(e)}"


@mcp.tool()
async def fetch_article_content(url: str) -> str:
    """
    Fetches the full text content of a source article from a given URL and strips HTML formatting.

    Args:
        url (str): The HTTP/HTTPS URL of the article to fetch.
    """
    try:
        logger.info(f"Tool fetch_article_content called for URL: {url}")
        content = await hn_client.fetch_article_content(url)
        return content
    except Exception as e:
        logger.exception(f"Error in fetch_article_content tool for URL {url}")
        return f"Error: Failed to fetch article content: {str(e)}"


def create_app() -> Starlette:
    """
    Creates and returns the Starlette application served via SSE.
    """
    logger.info("Initializing HackerNews MCP Server via SSE...")
    return mcp.sse_app()
