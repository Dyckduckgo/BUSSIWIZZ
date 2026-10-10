"""
Research Service Layer
High-level service coordinating:
UI / CLI -> ResearchService -> Orchestrator -> agents/tools -> SQLite Storage

Enforces:
- Health checks
- Zero credential exposure
- Graceful degradation and fallbacks
- Full session and snapshot persistence
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from orchestrator import ResearchOrchestrator
from storage.db import Database
from financial_data import FinancialMetrics
from agents.sec_agent import SECResearchReport


class ResearchService:
    """Core service managing research executions, tool health, and persistence."""

    def __init__(self, db_path: str = "data/research.db"):
        resolved_db_path = Path(db_path)
        if not resolved_db_path.is_absolute():
            resolved_db_path = Path(__file__).resolve().parent.parent / resolved_db_path
        self.db = Database(db_path=str(resolved_db_path))
        self.orchestrator = ResearchOrchestrator()

    def get_health_status(self) -> Dict[str, Any]:
        """
        Gathers health check diagnostics across all tools and database.
        Safe for UI presentation (no secret credentials exposed).
        """
        statuses = self.orchestrator.check_all_health()
        db_health = self.db.check_health()
        statuses["sqlite_db"] = {
            "status": "available" if db_health.get("status") == "healthy" else "unavailable",
            "tool": "sqlite_db",
            "active_mode": "local_sqlite",
            "message": f"SQLite database connected ({db_health.get('path')})",
        }
        return statuses

    async def execute_research(
        self,
        company_or_ticker: str,
        session_id: Optional[str] = None,
        include_papers: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end research session and persists all facts and metrics to SQLite.
        Returns the complete research result payload.
        """
        sid = session_id or f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        target = company_or_ticker.strip()

        # Run orchestration
        result = await self.orchestrator.run_research(target, include_papers=include_papers)
        result["session_id"] = sid

        # Prepare metrics for SQLite persistence
        fin_dict: Optional[Dict[str, Any]] = None
        metrics: Optional[FinancialMetrics] = result.get("financial_metrics")
        if metrics:
            fin_dict = {
                "current_price": metrics.current_price,
                "market_cap": metrics.market_cap,
                "revenue": metrics.revenue,
                "net_income": metrics.net_income,
                "eps": metrics.eps,
                "pe_ratio": metrics.pe_ratio,
                "ps_ratio": metrics.ps_ratio,
                "ev_ebitda": metrics.ev_ebitda,
                "gross_margin": metrics.gross_margin,
                "operating_margin": metrics.operating_margin,
                "free_cash_flow": metrics.free_cash_flow,
                "cash": metrics.cash,
                "debt": metrics.debt,
                "revenue_growth": metrics.revenue_growth,
                "eps_growth": metrics.eps_growth,
                "data_source": "yfinance",
            }

        # Prepare SEC facts for SQLite persistence
        sec_facts_list: List[Dict[str, Any]] = []
        sec_report: Optional[SECResearchReport] = result.get("sec_report")
        if sec_report and sec_report.facts:
            for fact in sec_report.facts:
                sec_facts_list.append({
                    "claim": fact.claim,
                    "value": fact.value,
                    "filing_type": fact.filing_type,
                    "filing_date": fact.filing_date,
                    "accession_number": fact.accession_number,
                    "source_url": fact.source_url,
                    "snippet": fact.source_snippet,
                })

        # Prepare Web sources for SQLite persistence
        web_sources_list: List[Dict[str, Any]] = result.get("sources", [])

        # Persist session to SQLite
        try:
            self.db.save_session(
                session_id=sid,
                company=result.get("company", target),
                ticker=result.get("ticker", target.upper()),
                status=result.get("status", "completed"),
                model_used=result.get("model_used", "none"),
                full_report=result.get("full_report", ""),
                financial_metrics=fin_dict,
                sec_facts=sec_facts_list,
                web_sources=web_sources_list,
                raw_data={
                    "fallbacks_used": result.get("fallbacks_used", []),
                    "web_source_mode": result.get("web_source_mode", ""),
                },
            )
        except Exception as db_err:
            result["fallbacks_used"].append(f"Database save warning: {str(db_err)}")

        return result

    def get_recent_history(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns list of recent research sessions."""
        return self.db.get_recent_sessions(limit=limit)

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Returns full session details from SQLite."""
        return self.db.get_session_by_id(session_id)
