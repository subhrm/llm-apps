"""
Hacker News API client and article scraper module.
Handles concurrent fetching of top stories and comments, as well as scraping
and cleaning webpage contents for LLM tools.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import httpx

# Configure logging
logger = logging.getLogger("hn_mcp.hn_client")

# Browser-like headers to prevent getting blocked by scrapers/CDNs
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


def clean_html(html_content: str) -> str:
    """
    Cleans HTML content (typically from HN comment text) into clean,
    readable plain text with formatting.
    """
    if not html_content:
        return ""
    
    # Parse comment text (which is typically clean but has simple HTML like <p>, <i>, <pre><code>)
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Add newlines for paragraph tags to preserve structure
    for p in soup.find_all("p"):
        p.insert_before("\n\n")
        
    # Format code blocks
    for code in soup.find_all("code"):
        code.insert_before(" `")
        code.insert_after("` ")

    # Format links nicely
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text()
        if href:
            if text and text != href:
                a.replace_with(f"[{text}]({href})")
            else:
                a.replace_with(href)
                
    text = soup.get_text()
    
    # Clean up redundant spacing/newlines
    lines = [line.strip() for line in text.splitlines()]
    cleaned_text = "\n".join(line for line in lines if line)
    return cleaned_text


def extract_clean_text(html_body: str) -> str:
    """
    Scrapes a full webpage, strips standard boilerplate (nav, footer, script, etc.),
    and extracts structured clean text content friendly for LLMs.
    """
    soup = BeautifulSoup(html_body, "html.parser")
    
    # Remove unwanted tags
    unwanted_tags = [
        "script", "style", "noscript", "header", "footer", "nav",
        "iframe", "svg", "form", "aside", "select", "button", "input"
    ]
    for tag in soup.find_all(unwanted_tags):
        tag.decompose()
        
    # Format headings
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        level = int(h.name[1])
        prefix = "#" * level
        h.insert_before(f"\n\n{prefix} ")
        h.insert_after("\n\n")
        
    # Format list items
    for li in soup.find_all("li"):
        li.insert_before("\n- ")
        
    # Format paragraph tags
    for p in soup.find_all("p"):
        p.insert_before("\n\n")
        p.insert_after("\n\n")

    # Format links
    for a in soup.find_all("a"):
        href = a.get("href", "")
        text = a.get_text().strip()
        if href and href.startswith("http"):
            if text and text != href:
                a.replace_with(f"[{text}]({href})")
            else:
                a.replace_with(href)

    # Try to find primary content container to narrow down search
    content_area = None
    for selector in ["article", "main", "[role='main']", ".post", ".article", ".content"]:
        found = soup.select_one(selector)
        if found:
            content_area = found
            break
            
    target_soup = content_area if content_area else soup.body if soup.body else soup
    
    text = target_soup.get_text()
    
    # Clean up multiple newlines
    lines = []
    consecutive_newlines = 0
    for line in text.splitlines():
        cleaned_line = line.strip()
        if cleaned_line:
            lines.append(cleaned_line)
            consecutive_newlines = 0
        else:
            if consecutive_newlines < 1:
                lines.append("")
                consecutive_newlines += 1
                
    return "\n".join(lines).strip()


class HackerNewsClient:
    """
    Asynchronous client for interacting with the Hacker News API
    and fetching source articles.
    """
    
    def __init__(self):
        # We configure limits for HTTPX client
        self.limits = httpx.Limits(max_keepalive_connections=5, max_connections=20)
        self.timeout = httpx.Timeout(15.0, connect=5.0)

    async def _fetch_json(self, url: str) -> Any:
        """Helper to fetch JSON data from a URL with retry logic."""
        async with httpx.AsyncClient(limits=self.limits, timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Error fetching JSON from {url}: {e}")
                raise

    async def fetch_item(self, item_id: int) -> dict[str, Any]:
        """Fetch item details by its Hacker News ID."""
        url = f"{HN_API_BASE}/item/{item_id}.json"
        return await self._fetch_json(url)

    async def fetch_top_stories(self, limit: int = 30) -> list[dict[str, Any]]:
        """
        Fetches the current top story IDs and resolves the top `limit` stories.
        """
        try:
            logger.info("Fetching top story IDs from Hacker News...")
            top_ids = await self._fetch_json(f"{HN_API_BASE}/topstories.json")
            if not top_ids:
                return []
            
            # Limit stories
            target_ids = top_ids[:limit]
            
            # Fetch all story details concurrently
            tasks = [self.fetch_item(story_id) for story_id in target_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            stories = []
            for i, result in enumerate(results):
                story_id = target_ids[i]
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch story {story_id}: {result}")
                    continue
                if not result:
                    continue
                
                # Format time
                time_val = result.get("time")
                readable_time = ""
                if time_val:
                    try:
                        readable_time = datetime.fromtimestamp(
                            time_val, tz=timezone.utc
                        ).strftime("%Y-%m-%d %H:%M:%S UTC")
                    except Exception:
                        pass
                
                story_url = result.get("url")
                hn_url = f"https://news.ycombinator.com/item?id={story_id}"
                
                stories.append({
                    "id": result.get("id"),
                    "title": result.get("title", "[No Title]"),
                    "url": story_url if story_url else hn_url,
                    "by": result.get("by", "anonymous"),
                    "score": result.get("score", 0),
                    "descendants": result.get("descendants", 0), # Comment count
                    "time": readable_time,
                    "hn_url": hn_url,
                    "is_self_post": story_url is None,
                })
                
            return stories
            
        except Exception as e:
            logger.error(f"Error fetching top stories: {e}")
            raise

    async def fetch_story_details(
        self, story_id: int, max_comments: int = 5
    ) -> dict[str, Any]:
        """
        Fetches a story details including its top comments, converting HTML comment text
        to clean plain text.
        """
        try:
            logger.info(f"Fetching story details for ID {story_id}...")
            story = await self.fetch_item(story_id)
            if not story:
                raise ValueError(f"Story with ID {story_id} not found.")
                
            comment_ids = story.get("kids", [])[:max_comments]
            comments = []
            
            if comment_ids:
                # Fetch comments concurrently
                tasks = [self.fetch_item(cid) for cid in comment_ids]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, res in enumerate(results):
                    cid = comment_ids[i]
                    if isinstance(res, Exception):
                        logger.warning(f"Failed to fetch comment {cid}: {res}")
                        continue
                    if not res or res.get("deleted") or res.get("dead"):
                        continue
                    
                    comments.append({
                        "id": res.get("id"),
                        "by": res.get("by", "anonymous"),
                        "text": clean_html(res.get("text", "")),
                        "time": datetime.fromtimestamp(
                            res.get("time", 0), tz=timezone.utc
                        ).strftime("%Y-%m-%d %H:%M:%S UTC")
                        if res.get("time") else ""
                    })
            
            story_url = story.get("url")
            hn_url = f"https://news.ycombinator.com/item?id={story_id}"
            
            return {
                "id": story.get("id"),
                "title": story.get("title", "[No Title]"),
                "url": story_url if story_url else hn_url,
                "by": story.get("by", "anonymous"),
                "score": story.get("score", 0),
                "descendants": story.get("descendants", 0),
                "time": datetime.fromtimestamp(
                    story.get("time", 0), tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M:%S UTC")
                if story.get("time") else "",
                "hn_url": hn_url,
                "comments": comments,
            }
            
        except Exception as e:
            logger.error(f"Error fetching story details: {e}")
            raise

    async def fetch_article_content(self, url: str) -> str:
        """
        Fetches the contents of the given article URL and parses it to clean body text.
        Handles errors gracefully.
        """
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return f"Error: Invalid URL scheme or network location: '{url}'"
            
        logger.info(f"Scraping content from URL: {url}...")
        
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=self.timeout,
            follow_redirects=True,
            verify=False  # Allow weak SSL configurations on some articles to prevent failure
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    # Non-HTML content, e.g., plain text or PDF. Try returning raw response text.
                    return f"[Non-HTML Content (Type: {content_type})]\n\n{response.text[:10000]}"
                
                clean_text = extract_clean_text(response.text)
                if not clean_text:
                    return "Error: Webpage loaded successfully, but failed to extract any readable body text."
                    
                return clean_text
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} fetching URL {url}: {e}")
                return f"Error: HTTP {e.response.status_code} occurred while trying to fetch the article."
            except httpx.ConnectTimeout:
                logger.error(f"Connection timeout fetching URL {url}")
                return "Error: Connection timed out while trying to reach the article server."
            except httpx.ReadTimeout:
                logger.error(f"Read timeout fetching URL {url}")
                return "Error: Read timed out while waiting for article server response."
            except Exception as e:
                logger.error(f"Unexpected error fetching URL {url}: {e}")
                return f"Error: Failed to fetch the article due to an unexpected error: {str(e)}"
