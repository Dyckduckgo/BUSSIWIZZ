"""
Integration and Unit Tests for Multi-Agent Stock Research Pipeline
Tests:
- Architecture: USER → ORCHESTRATOR → parallel research agents → evidence collection → VERIFIER → FINAL ANALYST → REPORT
- Research Agents: WebAgent, FinancialAgent, SECAgent, RDAgent
- Structured Pydantic Evidence models (claim, source_url, source_name, source_date, source_type, evidence_text, confidence, agent_name)
- Verifier 7 criteria audit:
  1. Source supports claim
  2. Source trustworthy
  3. Current/timely
  4. Numerical value correct
  5. Conclusion proportional to evidence
  6. No conflicting sources
  7. Fact vs inference vs speculation
- Final Analyst:
  - Relies ONLY on verified evidence for factual assertions
  - 11 core sections
  - Bull, Base, Bear scenario cases
  - Explainable 0-100 score across the 7 dimensions
  - Disclaimer check
- Complete pipeline test with NVIDIA (NVDA)
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock

from agents.models import (
    Evidence,
    VerifiedEvidence,
    VerificationReport,
    ResearchScore,
    ScenarioCases,
    AnalystReport,
)
from agents.web_agent import WebAgent
from agents.financial_agent import FinancialAgent
from agents.sec_agent import SECAgent, SECResearchReport
from agents.rd_agent import RDAgent, RDResearchReport, RDDiscovery, RDDevelopment
from agents.verifier import Verifier
from agents.analyst import FinalAnalyst
from agents.orchestrator import MultiAgentOrchestrator
from financial_data import FinancialMetrics


class TestMultiAgentPipelineComponents(unittest.TestCase):
    """Tests for individual agents, verifier checks, and analyst synthesis."""

    def test_evidence_model_schema(self):
        """Verifies that Evidence model encapsulates all required attributes."""
        ev = Evidence(
            claim="NVIDIA reported quarterly revenue of $35.1 billion.",
            source_url="https://sec.gov/edgar/nvda",
            source_name="SEC EDGAR Form 10-Q",
            source_date="2024-11-20",
            source_type="SEC_FILING",
            evidence_text="Total revenue for the third quarter was $35.1 billion.",
            confidence=0.99,
            agent_name="SECAgent",
            epistemic_status="FACT",
            numerical_value=35_100_000_000,
            metric_name="Revenue",
        )

        d = ev.to_dict()
        self.assertEqual(d["claim"], "NVIDIA reported quarterly revenue of $35.1 billion.")
        self.assertEqual(d["source_type"], "SEC_FILING")
        self.assertEqual(d["agent_name"], "SECAgent")
        self.assertEqual(d["confidence"], 0.99)
        self.assertEqual(d["numerical_value"], 35_100_000_000)

    def test_verifier_accepts_verified_evidence(self):
        """Verifies that legitimate institutional evidence passes all 7 verifier checks."""
        verifier = Verifier()
        ev = Evidence(
            claim="NVIDIA gross margin expanded to 75.0% in recent filings.",
            source_url="https://sec.gov/edgar/data/1045810",
            source_name="SEC Form 10-K",
            source_date="2025-02-26",
            source_type="SEC_FILING",
            evidence_text="Reported gross margin of 75.0% for fiscal year.",
            confidence=1.0,
            agent_name="SECAgent",
            epistemic_status="FACT",
            numerical_value=0.75,
            metric_name="Gross Margin",
        )

        result = verifier.verify_all([ev])
        self.assertEqual(result.verified_count, 1)
        self.assertEqual(result.rejected_count, 0)

        verified_item = result.verified_items[0]
        self.assertTrue(verified_item.verified)
        self.assertIn("Verified", verified_item.verification_reason)
        checks = verified_item.checks
        self.assertTrue(checks.source_supports_claim)
        self.assertTrue(checks.source_trustworthy)
        self.assertTrue(checks.is_current)
        self.assertTrue(checks.numerical_value_correct)
        self.assertTrue(checks.conclusion_proportional_to_evidence)
        self.assertTrue(checks.no_unresolved_conflicts)
        self.assertEqual(checks.epistemic_status, "FACT")

    def test_verifier_rejects_untrusted_and_speculative_evidence(self):
        """Verifies that verifier catches and rejects speculation, untrusted sources, and hyperbole."""
        verifier = Verifier()

        bad_evidence = [
            # 1. Speculation disguised as fact
            Evidence(
                claim="NVIDIA is rumored to launch an unannounced quantum accelerator next month.",
                source_url="https://leaks-blog.example.com/nvda",
                source_name="Anonymous Leak Blog",
                source_date="2026-01-01",
                source_type="NEWS",
                evidence_text="Rumors say a chip might be announced soon.",
                confidence=0.9,
                agent_name="WebAgent",
                epistemic_status="FACT",  # Improperly marked as FACT
            ),
            # 2. Hyperbolic conclusion stronger than evidence
            Evidence(
                claim="New GPU proves the stock will 10x and is guaranteed to bankrupt all competitors.",
                source_url="https://reuters.com/article",
                source_name="Reuters",
                source_date="2026-02-01",
                source_type="NEWS",
                evidence_text="NVIDIA announced a new GPU for enterprise servers.",
                confidence=0.8,
                agent_name="WebAgent",
                epistemic_status="FACT",
            ),
            # 3. Impossible / implausible numerical value
            Evidence(
                claim="Gross margin reached 250% of revenue.",
                source_url="https://sec.gov",
                source_name="SEC",
                source_date="2026-01-01",
                source_type="FINANCIAL_API",
                evidence_text="Gross margin recorded.",
                confidence=0.8,
                agent_name="FinancialAgent",
                numerical_value=2.5,
                metric_name="Gross Margin",
            ),
        ]

        result = verifier.verify_all(bad_evidence)
        self.assertEqual(result.rejected_count, 3)
        self.assertEqual(result.verified_count, 0)

        for item in result.rejected_items:
            self.assertFalse(item.verified)
            self.assertIn("Rejected", item.verification_reason)

    def test_final_analyst_11_sections_scenarios_and_score(self):
        """Verifies that the final analyst produces all 11 sections, 3 scenarios, and explainable score."""
        analyst = FinalAnalyst()

        mock_metrics = FinancialMetrics(
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            current_price=125.0,
            market_cap=3_050_000_000_000.0,
            revenue=96_300_000_000.0,
            net_income=53_000_000_000.0,
            eps=2.15,
            gross_margin=0.75,
            operating_margin=0.62,
            free_cash_flow=45_000_000_000.0,
            cash=34_000_000_000.0,
            debt=11_000_000_000.0,
            pe_ratio=42.0,
            ps_ratio=26.0,
            ev_ebitda=35.0,
            revenue_growth=1.22,
            eps_growth=1.65,
        )

        verified_ev = [
            VerifiedEvidence(
                evidence=Evidence(
                    claim="NVIDIA total revenue grew 122% YoY to $96.3B.",
                    source_url="https://sec.gov/edgar/nvda",
                    source_name="SEC Form 10-K",
                    source_date="2025-02-26",
                    source_type="SEC_FILING",
                    evidence_text="Total revenue increased 122% YoY.",
                    confidence=1.0,
                    agent_name="SECAgent",
                    epistemic_status="FACT",
                    numerical_value=96_300_000_000,
                    metric_name="Total Revenue",
                ),
                verified=True,
                verification_reason="Verified by official SEC 10-K filing.",
            )
        ]

        report = asyncio.run(
            analyst.analyze_async(
                company="NVIDIA Corporation",
                ticker="NVDA",
                verified_evidence=verified_ev,
                rejected_evidence=[],
                metrics=mock_metrics,
            )
        )

        self.assertIsInstance(report, AnalystReport)
        self.assertEqual(report.ticker, "NVDA")

        # Verify 11 Core Sections
        self.assertTrue(len(report.company_overview) > 20)
        self.assertTrue(len(report.financial_health) > 20)
        self.assertTrue(len(report.profitability) > 20)
        self.assertTrue(len(report.growth) > 20)
        self.assertTrue(len(report.valuation) > 20)
        self.assertTrue(len(report.competitive_advantage) > 20)
        self.assertTrue(len(report.management) > 20)
        self.assertTrue(len(report.rd_and_innovation) > 20)
        self.assertTrue(len(report.recent_developments) > 20)
        self.assertTrue(len(report.risks) > 20)
        self.assertTrue(len(report.catalysts) > 20)

        # Verify 3 Scenarios
        self.assertIn("Bull Case", report.scenarios.bull_case)
        self.assertIn("Base Case", report.scenarios.base_case)
        self.assertIn("Bear Case", report.scenarios.bear_case)

        # Verify Explainable Research Score across the 7 dimensions
        score = report.score
        self.assertGreaterEqual(score.total_score, 0.0)
        self.assertLessEqual(score.total_score, 100.0)
        self.assertGreaterEqual(score.business_quality, 0.0)
        self.assertLessEqual(score.business_quality, 20.0)
        self.assertGreaterEqual(score.financial_health, 0.0)
        self.assertLessEqual(score.financial_health, 20.0)
        self.assertGreaterEqual(score.growth, 0.0)
        self.assertLessEqual(score.growth, 15.0)
        self.assertGreaterEqual(score.competitive_advantage, 0.0)
        self.assertLessEqual(score.competitive_advantage, 15.0)
        self.assertGreaterEqual(score.valuation, 0.0)
        self.assertLessEqual(score.valuation, 15.0)
        self.assertGreaterEqual(score.rd_innovation, 0.0)
        self.assertLessEqual(score.rd_innovation, 10.0)
        self.assertGreaterEqual(score.risk_profile, 0.0)
        self.assertLessEqual(score.risk_profile, 5.0)

        # Verify sum matches composite score
        calculated_sum = round(
            score.business_quality
            + score.financial_health
            + score.growth
            + score.competitive_advantage
            + score.valuation
            + score.rd_innovation
            + score.risk_profile,
            1,
        )
        self.assertEqual(round(score.total_score, 1), calculated_sum)

        # Verify Compliance Disclaimer
        self.assertIn("Disclaimer", score.disclaimer)
        self.assertIn("personalized financial advice", score.disclaimer)


class TestFullPipelineWithNVIDIA(unittest.TestCase):
    """End-to-end integration test of the multi-agent pipeline with NVIDIA (NVDA)."""

    def setUp(self):
        self.orchestrator = MultiAgentOrchestrator()

    def test_pipeline_nvidia_execution(self):
        """
        Executes complete pipeline for NVIDIA:
        PARALLEL RESEARCH (Web, Financial, SEC, R&D)
        → EVIDENCE COLLECTION
        → VERIFIER AUDIT
        → FINAL ANALYST SYNTHESIS
        → INSTITUTIONAL REPORT
        """
        mock_metrics = FinancialMetrics(
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            current_price=128.50,
            market_cap=3_100_000_000_000.0,
            revenue=96_307_000_000.0,
            net_income=53_040_000_000.0,
            eps=2.15,
            gross_margin=0.753,
            operating_margin=0.618,
            free_cash_flow=45_200_000_000.0,
            cash=34_800_000_000.0,
            debt=11_200_000_000.0,
            pe_ratio=44.2,
            ps_ratio=26.5,
            ev_ebitda=36.0,
            revenue_growth=1.22,
            eps_growth=1.68,
        )

        mock_sec_report = SECResearchReport(
            company="NVIDIA Corporation",
            ticker="NVDA",
            cik="0001045810",
            filings={},
            facts=[],
            insider_transactions=[],
        )

        mock_rd_report = RDResearchReport(
            company="NVIDIA Corporation",
            ticker="NVDA",
            rd_spending={
                "latest_raw": 12_900_000_000,
                "latest_formatted": "$12.90B",
                "period_ended": "2025-01-26",
                "filed_date": "2025-02-26",
                "form": "10-K",
                "source_url": "https://sec.gov/Archives/edgar/data/1045810/nvda-10k.htm",
                "accession_number": "0001045810-25-000015",
            },
            discoveries=[
                RDDiscovery(
                    claim="Blackwell Ultra AI compute platform sampling with major hyperscalers.",
                    category="New products",
                    source_url="https://nvidianews.nvidia.com/blackwell",
                    source_name="NVIDIA Official Press Release",
                    publication_date="2025-10-15",
                    company_relevance="Direct revenue driver for datacenter compute.",
                    potential_business_impact="Maintains 70%+ gross margin on enterprise GPU clusters.",
                    confidence=0.98,
                    epistemic_status="FACT",
                ),
                RDDiscovery(
                    claim="Market rumors suggest a consumer RTX 6090 GPU might launch early next year.",
                    category="Products currently under development",
                    source_url="https://rumors.example.com/rtx6090",
                    source_name="Tech Rumor Leak Feed",
                    publication_date="2026-01-05",
                    company_relevance="Gaming segment hardware refresh.",
                    potential_business_impact="Speculative gaming sales boost.",
                    confidence=0.50,
                    epistemic_status="SPECULATION",
                ),
            ],
            major_developments=[
                RDDevelopment(
                    title="Blackwell AI GPU Architecture Scaling",
                    category="New products",
                    researching_building="Ultra-high-bandwidth multi-die GPU packaging with NVLink 5 interconnects.",
                    maturity="Commercial Production & Global Deployment",
                    why_it_matters="Delivers 4x faster LLM inference throughput per megawatt.",
                    market_affected="Global AI Cloud Hyperscalers and Sovereign AI Datacenters",
                    possible_financial_impact="Over $60 billion in anticipated multi-year delivery backlog.",
                    key_risks_or_barriers="TSMC advanced packaging bottlenecks and customer datacenter power limits.",
                    epistemic_status="FACT",
                    supporting_sources=["https://nvidianews.nvidia.com/blackwell"],
                    confidence=0.98,
                )
            ],
        )

        mock_web_evidence = [
            Evidence(
                claim="NVIDIA partners with major hyperscalers to deploy liquid-cooled AI superclusters.",
                source_url="https://reuters.com/technology/nvidia-superclusters",
                source_name="Reuters",
                source_date="2026-02-10",
                source_type="NEWS",
                evidence_text="NVIDIA confirmed partnerships with major cloud providers for liquid-cooled clusters.",
                confidence=0.92,
                agent_name="WebAgent",
                epistemic_status="FACT",
            )
        ]

        with patch.object(self.orchestrator.financial_agent, "run_async", return_value=(mock_metrics, [])):
            with patch.object(self.orchestrator.sec_agent, "run", return_value=mock_sec_report):
                with patch.object(self.orchestrator.rd_agent, "run_async", return_value=mock_rd_report):
                    with patch.object(self.orchestrator.web_agent, "run_async", return_value=mock_web_evidence):

                        result = asyncio.run(self.orchestrator.run_pipeline("NVIDIA"))

                        self.assertEqual(result["status"], "success")
                        self.assertEqual(result["ticker"], "NVDA")
                        self.assertEqual(result["company"], "NVIDIA Corporation")

                        # 1. Audit Log Verification
                        audit = result["audit_log"]
                        self.assertTrue(len(audit) >= 8)
                        self.assertTrue(any("WebAgent" in a for a in audit))
                        self.assertTrue(any("FinancialAgent" in a for a in audit))
                        self.assertTrue(any("SECAgent" in a for a in audit))
                        self.assertTrue(any("RDAgent" in a for a in audit))
                        self.assertTrue(any("Verifier" in a for a in audit))
                        self.assertTrue(any("FinalAnalyst" in a for a in audit))

                        # 2. Evidence Collection Verification
                        ev_collected = result["evidence_collected"]
                        self.assertGreaterEqual(len(ev_collected), 3)

                        # 3. Verifier Audit Verification
                        ver_report = result["verification_report"]
                        self.assertIsInstance(ver_report, VerificationReport)
                        self.assertGreaterEqual(ver_report.verified_count, 2)
                        # Verify that the rumor leak was rejected by verifier
                        self.assertTrue(any("rtx6090" in r.evidence.source_url for r in ver_report.rejected_items))

                        # 4. Final Analyst Report Verification
                        report = result["analyst_report"]
                        self.assertIsInstance(report, AnalystReport)

                        # Check 11 sections
                        full_md = result["full_report"]
                        self.assertIn("COMPANY OVERVIEW", full_md)
                        self.assertIn("FINANCIAL HEALTH", full_md)
                        self.assertIn("PROFITABILITY", full_md)
                        self.assertIn("GROWTH", full_md)
                        self.assertIn("VALUATION", full_md)
                        self.assertIn("COMPETITIVE ADVANTAGE", full_md)
                        self.assertIn("MANAGEMENT", full_md)
                        self.assertIn("R&D / INNOVATION", full_md)
                        self.assertIn("RECENT DEVELOPMENTS", full_md)
                        self.assertIn("RISKS", full_md)
                        self.assertIn("CATALYSTS", full_md)

                        # Check Scenarios
                        self.assertIn("Bull Case", full_md)
                        self.assertIn("Base Case", full_md)
                        self.assertIn("Bear Case", full_md)

                        # Check Scorecard
                        self.assertIn("EXECUTIVE RESEARCH SCORECARD", full_md)
                        self.assertIn("Business Quality", full_md)
                        self.assertIn("Financial Health", full_md)
                        self.assertIn("R&D / Innovation", full_md)
                        self.assertIn("Disclaimer", full_md)


if __name__ == "__main__":
    unittest.main()
