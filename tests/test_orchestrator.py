"""
Unit Tests for Research Orchestrator and Research Service
Verifies:
- Aggregate health checking across all tools
- Tool optionality and graceful handling when any tool raises or fails
- Local synthesis fallback when LLM is unavailable
- End-to-end service execution and SQLite persistence
- Zero credential exposure
"""

import os
import unittest
import tempfile
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from orchestrator import ResearchOrchestrator
from services.research_service import ResearchService
from financial_data import FinancialMetrics
from agents.sec_agent import SECResearchReport
from tools.sec.sec_parser import SECFilingMeta, SECExtractedFact


class TestOrchestratorAndService(unittest.TestCase):
    """Test suite for research orchestration and service layer."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_service.db")
        self.service = ResearchService(db_path=self.db_path)
        self.orchestrator = self.service.orchestrator

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_checks_aggregation(self):
        """Verifies health check output structure and absence of secret keys."""
        health = self.service.get_health_status()
        self.assertIn("searxng_mcp", health)
        self.assertIn("yfinance", health)
        self.assertIn("sec_edgar", health)
        self.assertIn("groq_llm", health)
        self.assertIn("sqlite_db", health)

        # Ensure no actual API key string appears in any message or status
        for tool, details in health.items():
            for k, v in details.items():
                if isinstance(v, str):
                    self.assertNotIn("gsk_", v, f"Potential credential leak in {tool}.{k}")

    def test_resilience_when_all_external_tools_fail(self):
        """Verifies that the orchestrator continues cleanly even if all tools fail."""
        with patch.object(self.orchestrator.yfinance_client, "get_financial_metrics_async", return_value=(None, "yfinance offline")):
            with patch.object(self.orchestrator.sec_agent, "run", side_effect=Exception("SEC blocked")):
                with patch.object(self.orchestrator.searxng_client, "search", return_value={"source": "direct_http_fallback", "results": []}):
                    # Also simulate Groq missing key / fallback
                    self.orchestrator.groq_api_key = None

                    result = asyncio.run(self.orchestrator.run_research("FAILED_CORP"))
                    self.assertEqual(result["status"], "success")
                    self.assertEqual(result["model_used"], "local_synthesis")
                    self.assertIn("1. Company Overview", result["full_report"])
                    self.assertIn("Major Risks", result["full_report"])
                    self.assertGreaterEqual(len(result["fallbacks_used"]), 1)

    def test_service_execute_and_persist(self):
        """Verifies full execution and database persistence."""
        mock_metrics = FinancialMetrics(
            symbol="TEST",
            company_name="Test Corp",
            current_price=150.0,
            market_cap=2_000_000_000.0,
            revenue=500_000_000.0,
        )

        mock_sec = SECResearchReport(
            company="Test Corp",
            ticker="TEST",
            cik="0001234567",
            filings={
                "10-K": [
                    SECFilingMeta(
                        form="10-K",
                        filing_date="2026-03-01",
                        accession_number="0001234567-26-000001",
                        primary_doc="form10k.htm",
                        source_url="https://sec.gov/doc",
                    )
                ]
            },
            facts=[
                SECExtractedFact(
                    company="Test Corp",
                    ticker="TEST",
                    claim="Revenue",
                    value="$500M",
                    filing_type="10-K",
                    filing_date="2026-03-01",
                    accession_number="0001234567-26-000001",
                    source_url="https://sec.gov/doc",
                    source_snippet="Annual revenue",
                )
            ],
            insider_transactions=[],
        )

        mock_web = {
            "source": "searxng_mcp",
            "results": [
                {
                    "title": "Test Corp Product Announcement",
                    "url": "https://example.com/news",
                    "snippet": "New product launched.",
                    "engine": "searxng",
                }
            ],
        }

        with patch.object(self.orchestrator.yfinance_client, "get_financial_metrics_async", return_value=(mock_metrics, None)):
            with patch.object(self.orchestrator.sec_agent, "run", return_value=mock_sec):
                with patch.object(self.orchestrator.searxng_client, "search", return_value=mock_web):
                    self.orchestrator.groq_api_key = None  # Use deterministic local synthesis

                    res = asyncio.run(self.service.execute_research("TEST"))
                    self.assertEqual(res["status"], "success")
                    self.assertEqual(res["company"], "Test Corp")
                    self.assertEqual(res["ticker"], "TEST")

                    # Verify SQLite persistence
                    session_id = res["session_id"]
                    db_session = self.service.get_session_by_id(session_id)
                    self.assertIsNotNone(db_session)
                    self.assertEqual(db_session["company"], "Test Corp")
                    self.assertEqual(db_session["ticker"], "TEST")
                    self.assertIsNotNone(db_session.get("financial_snapshot"))
                    self.assertEqual(db_session["financial_snapshot"]["current_price"], 150.0)
                    self.assertEqual(len(db_session.get("sec_facts", [])), 1)
                    self.assertEqual(len(db_session.get("web_sources", [])), 1)


if __name__ == "__main__":
    unittest.main()
