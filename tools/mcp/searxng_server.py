"""
SearXNG MCP Server
Provides open-source, local-first web search and URL reading tools via the Model Context Protocol (MCP).
Requires no paid external search API key.
"""

import os
import sys
import json
import asyncio
from typing import Optional, Dict, Any, List
import httpx

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server import MCPServer

# Default SearXNG URL (configurable via environment variable)
DEFAULT_SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8888")

# Initialize MCP server instance
server = MCPServer(name="searxng-research", version="1.0.0")


async def execute_searxng_search(
    query: str,
    searxng_url: Optional[str] = None,
    categories: str = "general,news",
    max_results: int = 5,
) -> Dict[str, Any]:
    """
    Direct asynchronous implementation of SearXNG search.
    Queries the SearXNG JSON endpoint and returns structured results.
    """
    base_url = (searxng_url or os.getenv("SEARXNG_URL") or DEFAULT_SEARXNG_URL).rstrip("/")
    search_url = f"{base_url}/search"
    params = {
        "q": query,
        "format": "json",
        "categories": categories,
        "language": "en",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        response = await client.get(search_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        results: List[Dict[str, Any]] = []
        raw_items = data.get("results", [])
        for item in raw_items[:max_results]:
            results.append({
                "title": (item.get("title") or "No title").strip(),
                "url": (item.get("url") or "").strip(),
                "snippet": (item.get("content") or "").strip(),
                "engine": item.get("engine", "searxng"),
                "published_date": item.get("publishedDate") or item.get("pubdate") or "",
            })

        return {
            "status": "success",
            "query": query,
            "source": "searxng_mcp",
            "count": len(results),
            "results": results,
        }


async def execute_read_page(url: str, max_length: int = 4000) -> Dict[str, Any]:
    """
    Direct asynchronous implementation of webpage content extraction.
    Fetches raw HTML and cleans boilerplate to extract readable article content.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

        if BeautifulSoup is not None:
            soup = BeautifulSoup(response.text, "html.parser")

            # Strip scripts, styles, forms, and navigation chrome
            for elem in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg"]):
                elem.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled Page"

            # Extract text from main structural content if available
            main_content = soup.find("main") or soup.find("article") or soup.find("body") or soup
            text = main_content.get_text(separator="\n", strip=True)
        else:
            import re
            html = response.text
            # Remove scripts, styles, navigation chrome
            html = re.sub(r"<(script|style|nav|footer|header|aside|noscript)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
            title_m = re.search(r"<title[^>]*>(.*?)</title>", response.text, flags=re.IGNORECASE | re.DOTALL)
            title = title_m.group(1).strip() if title_m else "Untitled Page"
            text = re.sub(r"<[^>]+>", " ", html)

        # Collapse excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned_text = "\n".join(lines)

        if len(cleaned_text) > max_length:
            cleaned_text = cleaned_text[:max_length] + "\n... [Content Truncated]"

        return {
            "status": "success",
            "url": url,
            "title": title,
            "content": cleaned_text,
            "length": len(cleaned_text),
        }


@server.tool(
    name="searxng_search",
    description="Searches the live web using a self-hosted SearXNG meta-search engine. Returns titles, snippets, and URLs."
)
async def searxng_search(query: str, categories: str = "general,news", max_results: int = 5) -> str:
    """MCP tool for web search via SearXNG."""
    try:
        data = await execute_searxng_search(query=query, categories=categories, max_results=max_results)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "message": "SearXNG search failed or instance is offline.",
            "source": "searxng_mcp"
        })


@server.tool(
    name="read_web_page",
    description="Reads and extracts clean, readable article text from any web page URL without ads or navigation clutter."
)
async def read_web_page(url: str, max_length: int = 4000) -> str:
    """MCP tool for webpage reading."""
    try:
        data = await execute_read_page(url=url, max_length=max_length)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({
            "status": "error",
            "url": url,
            "error": str(e),
            "message": "Failed to retrieve or parse webpage content."
        })


if __name__ == "__main__":
    # When run directly, start the MCP stdio transport loop
    asyncio.run(server.run_stdio_async())
