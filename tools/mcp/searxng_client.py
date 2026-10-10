"""
SearXNG MCP Client
Client wrapper for SearXNG MCP search and webpage reading.
Features:
- Health checking to detect whether local SearXNG is available.
- Seamless automatic fallback to direct HTTP search (Google News RSS / web scraping) if SearXNG is offline.
- No external paid API keys required.
"""

import os
import sys
import json
import asyncio
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import httpx

from .searxng_server import execute_searxng_search, execute_read_page, DEFAULT_SEARXNG_URL


class SearXNGClient:
    """Client for local SearXNG MCP research with zero-crash direct HTTP fallback."""

    def __init__(self, searxng_url: Optional[str] = None):
        self.searxng_url = (searxng_url or os.getenv("SEARXNG_URL") or DEFAULT_SEARXNG_URL).rstrip("/")

    def check_health(self) -> Dict[str, Any]:
        """
        Verifies if the local SearXNG instance is running and responding to JSON search.
        Returns health status and active operational mode.
        """
        try:
            # Check with a fast 1.5s timeout
            test_url = f"{self.searxng_url}/search"
            headers = {
                "User-Agent": "StockResearchAgent-HealthCheck/1.0",
                "Accept": "application/json",
            }
            params = {"q": "ping", "format": "json"}

            with httpx.Client(timeout=1.5) as client:
                res = client.get(test_url, params=params, headers=headers)
                if res.status_code == 200 and "application/json" in res.headers.get("content-type", ""):
                    data = res.json()
                    if "results" in data:
                        return {
                            "status": "available",
                            "tool": "searxng_mcp",
                            "url": self.searxng_url,
                            "active_mode": "searxng_mcp",
                            "message": "Local SearXNG instance is healthy and accessible.",
                        }

            return {
                "status": "unavailable",
                "tool": "searxng_mcp",
                "url": self.searxng_url,
                "active_mode": "direct_http_fallback",
                "message": f"SearXNG responded with non-JSON or status {res.status_code}. Using direct HTTP fallback.",
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "tool": "searxng_mcp",
                "url": self.searxng_url,
                "active_mode": "direct_http_fallback",
                "message": f"SearXNG is offline ({type(e).__name__}). Using direct HTTP fallback.",
            }

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Performs web search. First attempts to query SearXNG.
        If SearXNG is unavailable or errors out, automatically falls back to direct HTTP search.
        """
        # 1. Attempt SearXNG search
        try:
            searxng_res = await execute_searxng_search(
                query=query,
                searxng_url=self.searxng_url,
                max_results=max_results,
            )
            if searxng_res.get("status") == "success" and searxng_res.get("results"):
                return searxng_res
        except Exception:
            # Fall through to fallback
            pass

        # 2. Fallback to Direct HTTP Retrieval (Google News RSS & Web scraping)
        return await self._fallback_direct_http_search(query=query, max_results=max_results)

    async def _fallback_direct_http_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Fallback search mechanism using direct HTTP RSS retrieval.
        Requires zero paid API keys and works reliably.
        """
        try:
            encoded_query = urllib.parse.quote_plus(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            }

            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                res = await client.get(rss_url, headers=headers)
                res.raise_for_status()

            root = ET.fromstring(res.text)
            items = root.findall(".//item")

            results: List[Dict[str, Any]] = []
            for item in items[:max_results]:
                title = (item.find("title").text if item.find("title") is not None else "No Title").strip()
                link = (item.find("link").text if item.find("link") is not None else "").strip()
                pub_date = (item.find("pubDate").text if item.find("pubDate") is not None else "Recent").strip()

                if len(title) > 130:
                    title = title[:127] + "..."

                results.append({
                    "title": title,
                    "url": link,
                    "snippet": f"Published: {pub_date}",
                    "engine": "google_news_rss_fallback",
                    "published_date": pub_date,
                })

            return {
                "status": "success",
                "query": query,
                "source": "direct_http_fallback",
                "count": len(results),
                "results": results,
            }
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "source": "direct_http_fallback",
                "error": str(e),
                "count": 0,
                "results": [],
            }

    async def read_page(self, url: str, max_length: int = 4000) -> Dict[str, Any]:
        """
        Reads and extracts cleaned text from a webpage URL.
        """
        try:
            return await execute_read_page(url=url, max_length=max_length)
        except Exception as e:
            return {
                "status": "error",
                "url": url,
                "error": str(e),
                "content": "",
                "message": f"Failed to read webpage: {str(e)}",
            }

    def search_sync(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Synchronous wrapper for search."""
        return asyncio.run(self.search(query=query, max_results=max_results))

    def read_page_sync(self, url: str, max_length: int = 4000) -> Dict[str, Any]:
        """Synchronous wrapper for webpage reading."""
        return asyncio.run(self.read_page(url=url, max_length=max_length))
