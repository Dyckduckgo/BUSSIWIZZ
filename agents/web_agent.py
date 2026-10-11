"""
Web Research Agent
Specialist research agent for live web intelligence, earnings news, product launches,
and public industry commentary. Produces structured Evidence objects.
"""

import logging
from typing import List, Optional, Dict, Any

from tools.mcp.searxng_client import SearXNGClient
from agents.models import Evidence

logger = logging.getLogger("agents.web_agent")


class WebAgent:
    """Autonomous agent collecting structured web intelligence and news."""

    def __init__(self, searxng_client: Optional[SearXNGClient] = None):
        self.client = searxng_client or SearXNGClient()

    def check_health(self) -> Dict[str, Any]:
        """Health check for web research tools."""
        h = self.client.check_health()
        return {
            "status": h.get("status", "available"),
            "tool": "web_agent",
            "active_mode": h.get("active_mode", "web_search"),
            "message": h.get("message", "Web agent ready."),
        }

    async def run_async(self, company_or_ticker: str, max_results: int = 6) -> List[Evidence]:
        """
        Gathers live web news and strategic announcements.
        Returns a list of structured Evidence items.
        """
        logger.info(f"[WebAgent] Launching research for '{company_or_ticker}' using tools: SearXNG / Direct HTTP")
        clean_target = company_or_ticker.strip()
        evidence_list: List[Evidence] = []

        query = f"{clean_target} stock earnings business expansion strategy risks 2026"
        res = await self.client.search(query, max_results=max_results)

        if not res or res.get("status") != "success":
            logger.warning(f"[WebAgent] Web search returned no items or error: {res.get('error') if res else 'None'}")
            return evidence_list

        raw_results = res.get("results", [])
        engine_mode = res.get("source", "searxng_web")

        for r in raw_results:
            title = (r.get("title") or "").strip()
            snippet = (r.get("snippet") or "").strip()
            url = (r.get("url") or "").strip()
            pub_date = (r.get("published_date") or "").strip() or "Recent"

            if not title or len(title) < 8:
                continue

            # Classify epistemic status
            epistemic = "FACT"
            lower_text = f"{title} {snippet}".lower()
            if any(w in lower_text for w in ["rumor", "speculat", "unconfirmed", "might", "could potentially"]):
                epistemic = "SPECULATION"
            elif any(w in lower_text for w in ["analyst expects", "outlook", "estimated", "projected"]):
                epistemic = "INFERENCE"

            ev = Evidence(
                claim=title,
                source_url=url,
                source_name=f"Web News ({r.get('engine', engine_mode)})",
                source_date=pub_date,
                source_type="NEWS",
                evidence_text=snippet or title,
                confidence=0.85 if epistemic == "FACT" else 0.60,
                agent_name="WebAgent",
                epistemic_status=epistemic,
            )
            evidence_list.append(ev)

        logger.info(f"[WebAgent] Completed research. Gathered {len(evidence_list)} evidence items.")
        return evidence_list

    def run(self, company_or_ticker: str, max_results: int = 6) -> List[Evidence]:
        """Synchronous wrapper for run_async."""
        import asyncio
        return asyncio.run(self.run_async(company_or_ticker, max_results=max_results))
