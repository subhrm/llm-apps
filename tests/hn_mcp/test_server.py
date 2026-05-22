"""
Unit tests for the Hacker News MCP server tools and application factory.
Verifies tool definitions, return structure, parameter handling, and error cases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.applications import Starlette

from hn_mcp.server import (
    mcp,
    list_top_stories,
    get_story_details,
    fetch_article_content,
    create_app,
)


def test_mcp_metadata():
    """Verify that the FastMCP server is correctly initialized with the proper name."""
    assert mcp.name == "HackerNews"


def test_create_app():
    """Verify create_app creates a valid Starlette application instance."""
    app = create_app()
    assert isinstance(app, Starlette)


@pytest.mark.asyncio
async def test_list_top_stories_tool_success():
    """Test the list_top_stories tool behaves correctly on success."""
    mock_stories = [
        {"id": 1, "title": "A story", "url": "https://example.com"}
    ]
    
    with patch("hn_mcp.server.hn_client.fetch_top_stories", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_stories
        
        # Test default limit
        result = await list_top_stories()
        assert result == mock_stories
        mock_fetch.assert_called_once_with(limit=30)
        
        # Test manual limit within bounds
        mock_fetch.reset_mock()
        result = await list_top_stories(limit=15)
        assert result == mock_stories
        mock_fetch.assert_called_once_with(limit=15)


@pytest.mark.asyncio
async def test_list_top_stories_tool_limits():
    """Verify that limits in list_top_stories are clamped between 1 and 50."""
    with patch("hn_mcp.server.hn_client.fetch_top_stories", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []
        
        # Under limit
        await list_top_stories(limit=-5)
        mock_fetch.assert_called_with(limit=1)
        
        # Over limit
        mock_fetch.reset_mock()
        await list_top_stories(limit=100)
        mock_fetch.assert_called_with(limit=50)


@pytest.mark.asyncio
async def test_list_top_stories_tool_error():
    """Test that list_top_stories raises a RuntimeError on fetch failure."""
    with patch("hn_mcp.server.hn_client.fetch_top_stories", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = Exception("Firebase down")
        
        with pytest.raises(RuntimeError) as exc_info:
            await list_top_stories()
            
        assert "Failed to fetch top stories" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_story_details_tool_success():
    """Test the get_story_details tool constructs the Markdown output correctly."""
    mock_details = {
        "id": 123,
        "title": "Clean Code",
        "by": "unclebob",
        "score": 500,
        "descendants": 3,
        "time": "2026-05-23 00:00:00 UTC",
        "url": "https://example.com/clean",
        "hn_url": "https://news.ycombinator.com/item?id=123",
        "comments": [
            {"id": 456, "by": "bob", "text": "Very clean indeed.", "time": "2026-05-23 00:05:00 UTC"},
            {"id": 789, "by": "alice", "text": "Agreed.", "time": "2026-05-23 00:10:00 UTC"}
        ]
    }
    
    with patch("hn_mcp.server.hn_client.fetch_story_details", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_details
        
        result = await get_story_details(story_id=123, max_comments=2)
        
        # Verify title, metadata, and comments are printed
        assert "# Clean Code" in result
        assert "Author:** `unclebob`" in result
        assert "Score:** `500 points`" in result
        assert "Top 2 Comments" in result
        assert "Comment by bob" in result
        assert "Very clean indeed." in result
        assert "Comment by alice" in result
        assert "Agreed." in result
        
        mock_fetch.assert_called_once_with(123, max_comments=2)


@pytest.mark.asyncio
async def test_get_story_details_tool_clamping():
    """Verify that comment count is clamped between 0 and 20."""
    with patch("hn_mcp.server.hn_client.fetch_story_details", new_callable=AsyncMock) as mock_fetch:
        # Mock returns minimal details to bypass markdown formatting errors
        mock_fetch.return_value = {
            "id": 1, "title": "T", "by": "A", "score": 1, "descendants": 0,
            "time": "T", "url": "U", "hn_url": "H", "comments": []
        }
        
        # Under max_comments
        await get_story_details(story_id=1, max_comments=-5)
        mock_fetch.assert_called_with(1, max_comments=0)
        
        # Over max_comments
        mock_fetch.reset_mock()
        await get_story_details(story_id=1, max_comments=50)
        mock_fetch.assert_called_with(1, max_comments=20)


@pytest.mark.asyncio
async def test_get_story_details_tool_error():
    """Test that get_story_details returns an error message on failure."""
    with patch("hn_mcp.server.hn_client.fetch_story_details", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = Exception("Not found")
        
        result = await get_story_details(story_id=999)
        assert "Error: Failed to fetch story details" in result


@pytest.mark.asyncio
async def test_fetch_article_content_tool_success():
    """Test that fetch_article_content tool forwards request to clean client scraper."""
    with patch("hn_mcp.server.hn_client.fetch_article_content", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.return_value = "Extracted body text content."
        
        result = await fetch_article_content("https://example.com/article")
        assert result == "Extracted body text content."
        mock_scrape.assert_called_once_with("https://example.com/article")


@pytest.mark.asyncio
async def test_fetch_article_content_tool_error():
    """Test fetch_article_content returns error description on failure."""
    with patch("hn_mcp.server.hn_client.fetch_article_content", new_callable=AsyncMock) as mock_scrape:
        mock_scrape.side_effect = Exception("Connection refused")
        
        result = await fetch_article_content("https://example.com/article")
        assert "Error: Failed to fetch article content" in result
