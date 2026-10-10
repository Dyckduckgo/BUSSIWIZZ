"""
OpenAlex Academic Paper Research Client (Optional)
Uses the free, public OpenAlex REST API (zero API key required).
Provides scientific literature and academic research papers for company technology/R&D.
"""

import os
import urllib.parse
from typing import Dict, Any, List, Optional
import httpx


class OpenAlexClient:
    """Free, public academic paper research client (requires no API key)."""

    BASE_URL = "https://api.openalex.org"

    def check_health(self) -> Dict[str, Any]:
        """Checks OpenAlex public API availability."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.BASE_URL}/works?search=test&per-page=1")
                if res.status_code == 200:
                    return {
                        "status": "available",
                        "tool": "openalex_papers",
                        "active_mode": "public_api",
                        "message": "OpenAlex public academic API is healthy (zero key required).",
                    }
                return {
                    "status": "degraded",
                    "tool": "openalex_papers",
                    "active_mode": "public_api",
                    "message": f"OpenAlex returned status {res.status_code}.",
                }
        except Exception as e:
            return {
                "status": "unavailable",
                "tool": "openalex_papers",
                "active_mode": "disabled",
                "message": f"OpenAlex is offline or unreachable ({type(e).__name__}).",
            }

    async def search_papers(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """Fetches relevant research papers from OpenAlex."""
        try:
            encoded_query = urllib.parse.quote_plus(query)
            url = f"{self.BASE_URL}/works?search={encoded_query}&per-page={max_results}"
            headers = {"User-Agent": "StockResearchAgent/1.0 (mailto:research@busswizz-finance.local)"}

            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(url, headers=headers)
                res.raise_for_status()
                data = res.json()

            results: List[Dict[str, Any]] = []
            for item in data.get("results", []):
                authors = [a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])]
                results.append({
                    "title": item.get("title") or "Untitled Paper",
                    "publication_year": item.get("publication_year"),
                    "doi": item.get("doi"),
                    "url": item.get("doi") or item.get("id"),
                    "cited_by_count": item.get("cited_by_count", 0),
                    "authors": authors[:3],
                })

            return {
                "status": "success",
                "source": "openalex",
                "count": len(results),
                "results": results,
            }
        except Exception as e:
            return {
                "status": "error",
                "source": "openalex",
                "error": str(e),
                "count": 0,
                "results": [],
            }
