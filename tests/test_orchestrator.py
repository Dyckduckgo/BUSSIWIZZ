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
from agents.rd_agent import RDAgent, RDResearchReport, RDDiscovery, RDDevelopment
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
        self.assertIn("rd_agent", health)
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
                with patch.object(self.orchestrator.rd_agent, "run_async", side_effect=Exception("R&D agent error")):
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
        """Verifies full execution and database persistence across all agents."""
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

        mock_rd = RDResearchReport(
            company="Test Corp",
            ticker="TEST",
            rd_spending={
                "latest_raw": 50_000_000,
                "latest_formatted": "$50.00M",
                "period_ended": "2025-12-31",
                "filed_date": "2026-03-01",
                "form": "10-K",
                "source_url": "https://sec.gov/doc",
            },
            discoveries=[
                RDDiscovery(
                    claim="Test Corp launched AI accelerator architecture.",
                    category="New products",
                    source_url="https://example.com/ai",
                    source_name="Tech News",
                    publication_date="2026-01-10",
                    company_relevance="Primary new product line.",
                    potential_business_impact="Drives margin expansion.",
                    confidence=0.95,
                    epistemic_status="FACT",
                )
            ],
            major_developments=[
                RDDevelopment(
                    title="Next-Gen AI Hardware Accelerator",
                    category="New products",
                    researching_building="Custom ASIC processor for AI inference.",
                    maturity="Commercial Production",
                    why_it_matters="Reduces third-party GPU costs.",
                    market_affected="Cloud Datacenter Market",
                    possible_financial_impact="Projected $100M revenue run rate.",
                    key_risks_or_barriers="Supply chain fabrication yield constraints.",
                    epistemic_status="FACT",
                    supporting_sources=["https://example.com/ai"],
                    confidence=0.95,
                )
            ],
            category_summary={"New products": 1, "Company R&D spending": 1},
            sources=[{"title": "AI Accelerator Launch", "url": "https://example.com/ai", "name": "Tech News"}],
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
                with patch.object(self.orchestrator.rd_agent, "run_async", return_value=mock_rd):
                    with patch.object(self.orchestrator.searxng_client, "search", return_value=mock_web):
                        self.orchestrator.groq_api_key = None  # Use deterministic local synthesis

                        res = asyncio.run(self.service.execute_research("TEST"))
                        self.assertEqual(res["status"], "success")
                        self.assertEqual(res["company"], "Test Corp")
                        self.assertEqual(res["ticker"], "TEST")
                        self.assertIsNotNone(res.get("rd_report"))

                        # Verify SQLite persistence
                        session_id = res["session_id"]
                        db_session = self.service.get_session_by_id(session_id)
                        self.assertIsNotNone(db_session)
                        self.assertEqual(db_session["company"], "Test Corp")
                        self.assertEqual(db_session["ticker"], "TEST")
                        self.assertIsNotNone(db_session.get("financial_snapshot"))
                        self.assertEqual(db_session["financial_snapshot"]["current_price"], 150.0)
                        self.assertEqual(len(db_session.get("sec_facts", [])), 1)
                        self.assertEqual(len(db_session.get("web_sources", [])), 2)  # web + rd
                        self.assertEqual(len(db_session.get("rd_discoveries", [])), 1)

    def test_concurrent_execution_financial_sec_and_rd_agents(self):
        """Verifies that the financial, SEC, and R&D agents all run concurrently and synthesize together."""
        mock_metrics = FinancialMetrics(
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            current_price=120.0,
            market_cap=3_000_000_000_000.0,
            revenue=100_000_000_000.0,
        )

        mock_sec = SECResearchReport(
            company="NVIDIA Corporation",
            ticker="NVDA",
            cik="0001045810",
            filings={},
            facts=[],
            insider_transactions=[],
        )

        mock_rd = RDResearchReport(
            company="NVIDIA Corporation",
            ticker="NVDA",
            rd_spending={
                "latest_formatted": "$12.90B",
                "form": "10-K",
                "period_ended": "2025-01-26",
                "filed_date": "2025-02-26",
                "source_url": "https://sec.gov/filing",
            },
            discoveries=[
                RDDiscovery(
                    claim="Blackwell Ultra GPU sampling with tier-1 cloud providers.",
                    category="New products",
                    source_url="https://nvidia.com/blackwell",
                    source_name="NVIDIA Press Release",
                    publication_date="2025-09-01",
                    company_relevance="Flagship datacenter AI compute engine.",
                    potential_business_impact="Sustains 75%+ gross margins.",
                    confidence=0.95,
                    epistemic_status="FACT",
                )
            ],
            major_developments=[
                RDDevelopment(
                    title="Blackwell Ultra Datacenter Compute",
                    category="New products",
                    researching_building="Massive multi-die GPU packaging with NVLink 5.",
                    maturity="Commercial Scaling",
                    why_it_matters="Industry benchmark for LLM inference efficiency.",
                    market_affected="Global AI Hyperscaler Datacenters",
                    possible_financial_impact="Over $50B in forward pipeline orders.",
                    key_risks_or_barriers="TSMC CoWoS advanced packaging capacity.",
                    epistemic_status="FACT",
                )
            ],
        )

        with patch.object(self.orchestrator.yfinance_client, "get_financial_metrics_async", return_value=(mock_metrics, None)):
            with patch.object(self.orchestrator.sec_agent, "run", return_value=mock_sec):
                with patch.object(self.orchestrator.rd_agent, "run_async", return_value=mock_rd):
                    with patch.object(self.orchestrator.searxng_client, "search", return_value={"source": "searxng_mcp", "results": []}):
                        self.orchestrator.groq_api_key = None

                        res = asyncio.run(self.orchestrator.run_research("NVDA"))
                        self.assertEqual(res["status"], "success")
                        self.assertEqual(res["company"], "NVIDIA Corporation")
                        self.assertIsNotNone(res["financial_metrics"])
                        self.assertIsNotNone(res["sec_report"])
                        self.assertIsNotNone(res["rd_report"])

                        full_report = res["full_report"]
                        # Verify R&D spending was integrated into synthesis
                        self.assertIn("$12.90B", full_report)
                        # Verify Major Developments & 6-point evaluation in synthesis
                        self.assertIn("Blackwell Ultra", full_report)
                        self.assertIn("What Company is Researching/Building", full_report)
                        self.assertIn("How Mature Is It", full_report)
                        self.assertIn("Why Does It Matter", full_report)
                        self.assertIn("What Market Could It Affect", full_report)
                        self.assertIn("Possible Financial Impact", full_report)
                        self.assertIn("What Could Prevent It From Succeeding", full_report)


if __name__ == "__main__":
    unittest.main()
