"""
Unit and Integration Tests for ResearchService Layer
Verifies:
1. Flet UI -> ResearchService -> Orchestrator -> Agents architecture
2. async research_company(ticker, market) pipeline execution
3. Structured ResearchResult generation with to_dict() schema matching UI tabs
4. Live progress callback reporting all 6 stages
5. Timeout handling with user-friendly error formatting
6. Cancellation handling with clean status updates
7. Backward compatibility for execute_research() and get_health_status()
"""

import unittest
import asyncio
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock

from services.research_service import ResearchService, ResearchResult
from agents.models import (
    Evidence,
    VerifiedEvidence,
    VerificationReport,
    ResearchScore,
    ScenarioCases,
    AnalystReport,
)
from financial_data import FinancialMetrics


class TestResearchService(unittest.IsolatedAsyncioTestCase):
    """Test suite for ResearchService execution, progress callbacks, timeouts, and error handling."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_research.db")
        self.service = ResearchService(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_mock_pipeline_result(self, ticker: str = "NVDA") -> dict:
        score = ResearchScore(
            total_score=91.5,
            business_quality=18.5,
            financial_health=19.0,
            growth=14.0,
            competitive_advantage=14.0,
            valuation=9.0,
            rd_innovation=9.0,
            risk_profile=4.0,
            explanation="Superior margins, robust balance sheet, and leadership in AI.",
        )
        scenarios = ScenarioCases(
            bull_case="Hyperscaler compute capex accelerates.",
            base_case="Steady 25% revenue expansion matching data center demand.",
            bear_case="Potential customer inventory digestion.",
        )
        report = AnalystReport(
            company="NVIDIA Corporation",
            ticker=ticker,
            company_overview="NVIDIA is the pioneer of GPU-accelerated computing.",
            financial_health="Strong net cash positive position.",
            profitability="Gross margin exceeds 70%.",
            growth="Triple-digit year-over-year revenue expansion.",
            valuation="Trading at a premium but justified multiple.",
            competitive_advantage="CUDA ecosystem and proprietary interconnects.",
            management="Visionary execution under founder leadership.",
            rd_and_innovation="Blackwell and Rubin architectures in active roadmap.",
            recent_developments="Volume shipments of flagship liquid-cooled server racks.",
            risks="Supply chain concentration at advanced packaging fabs.",
            catalysts="Enterprise generative AI deployments.",
            scenarios=scenarios,
            score=score,
            verified_evidence_count=5,
            rejected_evidence_count=1,
            full_markdown="# Institutional Equity Report: NVDA",
        )
        metrics = FinancialMetrics(
            symbol=ticker,
            company_name="NVIDIA Corporation",
            current_price=135.50,
            market_cap=3300000000000,
            revenue=96000000000,
            net_income=53000000000,
            eps=2.15,
            pe_ratio=45.2,
            ps_ratio=28.5,
            ev_ebitda=38.0,
            gross_margin=0.75,
            operating_margin=0.62,
            free_cash_flow=45000000000,
            cash=34000000000,
            debt=10000000000,
            revenue_growth=1.22,
            eps_growth=1.68,
        )
        return {
            "run_id": "run_test_12345",
            "company": "NVIDIA Corporation",
            "ticker": ticker,
            "status": "success",
            "research_score": score,
            "analyst_report": report,
            "verification_report": VerificationReport(
                total_claims=6,
                verified_count=5,
                rejected_count=1,
                verified_items=[],
                rejected_items=[],
            ),
            "financial_metrics": metrics,
            "rd_report": None,
            "sec_report": None,
            "sources": [{"title": "Official 10-K", "url": "https://sec.gov", "type": "SEC Filing"}],
            "full_report": report.full_markdown,
            "report_path": "data/reports/NVDA_run_test_12345.md",
        }

    async def test_research_company_success(self):
        """Verifies end-to-end execution of research_company returning ResearchResult."""
        mock_payload = self._create_mock_pipeline_result("NVDA")

        with patch.object(
            self.service.multi_agent_orchestrator,
            "run_pipeline",
            new_callable=AsyncMock,
            return_value=mock_payload,
        ):
            progress_events = []

            def on_progress(stages):
                progress_events.append(stages)

            result = await self.service.research_company(
                ticker="NVDA",
                market="NASDAQ",
                on_progress=on_progress,
                timeout=30.0,
            )

            self.assertIsInstance(result, ResearchResult)
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.ticker, "NVDA")
            self.assertEqual(result.company, "NVIDIA Corporation")
            self.assertAlmostEqual(result.overall_score, 91.5, places=1)
            self.assertIn("A", result.score_grade)

            # Test schema conversion for Flet dashboard tabs
            ui_dict = result.to_dict()
            self.assertIn("overview", ui_dict)
            self.assertIn("financials", ui_dict)
            self.assertIn("rnd", ui_dict)
            self.assertIn("news", ui_dict)
            self.assertIn("risks", ui_dict)
            self.assertIn("scenarios", ui_dict)
            self.assertIn("sources", ui_dict)
            self.assertIn("history", ui_dict)
            self.assertIn("progress_steps", ui_dict)
            self.assertEqual(len(ui_dict["progress_steps"]), 6)

            # Check that progress events were triggered
            self.assertGreater(len(progress_events), 0)

    async def test_empty_ticker_validation(self):
        """Verifies that an empty ticker returns a user-friendly error without crashing."""
        result = await self.service.research_company(ticker="")
        self.assertEqual(result.status, "failed")
        self.assertIn("valid stock symbol", result.error_message)

    async def test_timeout_handling(self):
        """Verifies that timeout handling aborts slow jobs and returns clear messaging."""
        async def slow_pipeline(*args, **kwargs):
            await asyncio.sleep(2.0)
            return self._create_mock_pipeline_result("AAPL")

        with patch.object(
            self.service.multi_agent_orchestrator,
            "run_pipeline",
            side_effect=slow_pipeline,
        ):
            result = await self.service.research_company(
                ticker="AAPL",
                market="NASDAQ",
                timeout=0.1,  # Ultra-short timeout to trigger guard
            )

            self.assertEqual(result.status, "failed")
            self.assertIn("timed out", result.error_message)
            self.assertIn("AAPL", result.error_message)

    async def test_cancellation_handling(self):
        """Verifies that cancel_research gracefully terminates execution."""
        async def mock_running_pipeline(*args, **kwargs):
            self.service.cancel_research("TSLA")
            await asyncio.sleep(0.01)
            raise asyncio.CancelledError()

        with patch.object(
            self.service.multi_agent_orchestrator,
            "run_pipeline",
            side_effect=mock_running_pipeline,
        ):
            result = await self.service.research_company(ticker="TSLA")
            self.assertEqual(result.status, "cancelled")
            self.assertIn("cancelled", result.error_message.lower())

    async def test_user_friendly_error_formatting(self):
        """Verifies that exceptions are transformed into readable diagnostic messages."""
        with patch.object(
            self.service.multi_agent_orchestrator,
            "run_pipeline",
            side_effect=ConnectionError("getaddrinfo failed for api.nasdaq.com"),
        ):
            result = await self.service.research_company(ticker="MSFT")
            self.assertEqual(result.status, "failed")
            self.assertIn("internet connection", result.error_message.lower())

    def test_health_checks_aggregation(self):
        """Verifies health diagnostics with zero credential leaks."""
        health = self.service.get_health_status()
        self.assertIn("sqlite_db", health)
        self.assertEqual(health["sqlite_db"]["status"], "available")
        for tool, details in health.items():
            for k, v in details.items():
                if isinstance(v, str):
                    self.assertNotIn("gsk_", v)
                    self.assertNotIn("Bearer ", v)

    async def test_backward_compatibility_execute_research(self):
        """Verifies existing CLI endpoint execute_research remains operational."""
        mock_payload = self._create_mock_pipeline_result("NVDA")
        with patch.object(
            self.service.multi_agent_orchestrator,
            "run_pipeline",
            new_callable=AsyncMock,
            return_value=mock_payload,
        ):
            res = await self.service.execute_research("NVDA")
            self.assertIn("session_id", res)
            self.assertEqual(res["ticker"], "NVDA")


if __name__ == "__main__":
    unittest.main()
