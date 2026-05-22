"""
Unit tests for the HackerNewsClient class, HTML cleaning utilities,
and webpage text extraction tools.
"""
import asyncio
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from hn_mcp.hn_client import (
    HackerNewsClient,
    clean_html,
    extract_clean_text,
)


def test_clean_html_basic():
    """Test the clean_html helper with basic HTML strings."""
    assert clean_html("") == ""
    assert clean_html(None) == ""
    
    # Test paragraph insertion
    html = "Hello<p>World</p>"
    cleaned = clean_html(html)
    assert "Hello" in cleaned
    assert "World" in cleaned
    
    # Test link formatting
    html_link = 'Visit <a href="https://example.com">Example</a> site'
    cleaned_link = clean_html(html_link)
    assert "[Example](https://example.com)" in cleaned_link
    
    # Test code block formatting
    html_code = "Code: <code>import sys</code>"
    cleaned_code = clean_html(html_code)
    assert "`import sys`" in cleaned_code


def test_extract_clean_text_stripping():
    """Test extract_clean_text correctly strips scripts and formats elements."""
    html_body = """
    <html>
        <head><title>Test Title</title></head>
        <body>
            <nav><a href="/home">Home</a></nav>
            <main>
                <h1>Article Main Title</h1>
                <p>First paragraph of the article with a <a href="https://google.com">link</a>.</p>
                <script>console.log("hello");</script>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </main>
            <footer>Footer notes</footer>
        </body>
    </html>
    """
    cleaned = extract_clean_text(html_body)
    
    # Should contain title and content
    assert "Article Main Title" in cleaned
    assert "First paragraph of the article" in cleaned
    assert "[link](https://google.com)" in cleaned
    assert "Item 1" in cleaned
    assert "Item 2" in cleaned
    
    # Should NOT contain nav, script, footer content
    assert "Home" not in cleaned
    assert "console.log" not in cleaned
    assert "Footer notes" not in cleaned


@pytest.mark.asyncio
async def test_fetch_json_success():
    """Test successful JSON fetching via _fetch_json."""
    client = HackerNewsClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value"}
    mock_response.raise_for_status = MagicMock()
    
    # Mock the HTTPX async client's get method
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await client._fetch_json("https://api.example.com/data")
        assert result == {"key": "value"}
        mock_get.assert_called_once_with("https://api.example.com/data")


@pytest.mark.asyncio
async def test_fetch_item():
    """Test fetching a single Hacker News item by ID."""
    client = HackerNewsClient()
    
    dummy_item = {
        "id": 12345,
        "type": "story",
        "title": "Test Story",
        "by": "testuser",
    }
    
    with patch.object(client, "_fetch_json", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = dummy_item
        
        item = await client.fetch_item(12345)
        assert item == dummy_item
        mock_fetch.assert_called_once_with("https://hacker-news.firebaseio.com/v0/item/12345.json")


@pytest.mark.asyncio
async def test_fetch_top_stories():
    """Test fetching and resolving the top stories list."""
    client = HackerNewsClient()
    
    # Mock top stories IDs response
    top_ids = [1, 2]
    
    # Mock resolved items
    item_1 = {
        "id": 1,
        "type": "story",
        "title": "Story 1",
        "by": "author1",
        "score": 100,
        "descendants": 5,
        "time": 1700000000,
        "url": "https://example1.com",
    }
    item_2 = {
        "id": 2,
        "type": "story",
        "title": "Story 2",
        "by": "author2",
        "score": 200,
        "descendants": 10,
        "time": 1700000050,
        "url": None, # Ask HN / Self post
    }
    
    async def mock_fetch_json(url):
        if "topstories.json" in url:
            return top_ids
        raise ValueError("Unexpected url")
        
    async def mock_fetch_item(item_id):
        if item_id == 1:
            return item_1
        if item_id == 2:
            return item_2
        return None

    with patch.object(client, "_fetch_json", side_effect=mock_fetch_json), \
         patch.object(client, "fetch_item", side_effect=mock_fetch_item):
         
        stories = await client.fetch_top_stories(limit=2)
        
        assert len(stories) == 2
        
        # Verify first story parsing
        assert stories[0]["id"] == 1
        assert stories[0]["title"] == "Story 1"
        assert stories[0]["url"] == "https://example1.com"
        assert stories[0]["by"] == "author1"
        assert stories[0]["score"] == 100
        assert stories[0]["descendants"] == 5
        assert stories[0]["is_self_post"] is False
        assert "2023-" in stories[0]["time"]  # Readable timestamp contains year
        
        # Verify second story parsing (self post / Ask HN)
        assert stories[1]["id"] == 2
        assert stories[1]["title"] == "Story 2"
        assert stories[1]["url"] == "https://news.ycombinator.com/item?id=2"
        assert stories[1]["is_self_post"] is True


@pytest.mark.asyncio
async def test_fetch_story_details():
    """Test fetching full details of a story and its top comments."""
    client = HackerNewsClient()
    
    story_item = {
        "id": 999,
        "type": "story",
        "title": "Fascinating Story",
        "by": "op_user",
        "score": 150,
        "time": 1700000000,
        "url": "https://example.com/story",
        "descendants": 2,
        "kids": [1001, 1002],
    }
    
    comment_1 = {
        "id": 1001,
        "type": "comment",
        "by": "commenter1",
        "text": "Great post! Visit <a href='https://link.com'>Link</a>",
        "time": 1700000100,
    }
    
    comment_2 = {
        "id": 1002,
        "type": "comment",
        "by": "commenter2",
        "text": "Interesting perspective.",
        "time": 1700000200,
    }
    
    async def mock_fetch_item(item_id):
        if item_id == 999:
            return story_item
        if item_id == 1001:
            return comment_1
        if item_id == 1002:
            return comment_2
        return None
        
    with patch.object(client, "fetch_item", side_effect=mock_fetch_item):
        details = await client.fetch_story_details(story_id=999, max_comments=2)
        
        assert details["id"] == 999
        assert details["title"] == "Fascinating Story"
        assert details["by"] == "op_user"
        assert len(details["comments"]) == 2
        
        # Verify comment parsing
        assert details["comments"][0]["by"] == "commenter1"
        assert "[Link](https://link.com)" in details["comments"][0]["text"]
        assert details["comments"][1]["by"] == "commenter2"
        assert details["comments"][1]["text"] == "Interesting perspective."


@pytest.mark.asyncio
async def test_fetch_article_content_success():
    """Test successful scraping of article body content from a URL."""
    client = HackerNewsClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = "<html><body><article><p>This is the article main content.</p></article></body></html>"
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        content = await client.fetch_article_content("https://example.com/my-article")
        assert content == "This is the article main content."
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_article_content_non_html():
    """Test scraping of non-HTML content returns plain text fallback."""
    client = HackerNewsClient()
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/plain"}
    mock_response.text = "Raw plain text body content"
    mock_response.raise_for_status = MagicMock()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        content = await client.fetch_article_content("https://example.com/doc.txt")
        assert "[Non-HTML Content" in content
        assert "Raw plain text body content" in content


@pytest.mark.asyncio
async def test_fetch_article_content_http_error():
    """Test graceful handling of HTTP connection and status errors."""
    client = HackerNewsClient()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # HTTP Status Error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=mock_response))
        mock_get.return_value = mock_response
        
        content = await client.fetch_article_content("https://example.com/missing")
        assert "Error: HTTP 404" in content
        
        # Connection Timeout Error
        mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")
        content = await client.fetch_article_content("https://example.com/slow")
        assert "timed out while trying to reach the article server" in content
