"""
Unit Tests for R&D and Technology Research Agent (RDAgent)
Verifies:
- Complete discovery schema validation matching the required specification
- Epistemic classification: FACT, INFERENCE, SPECULATION
- Strict enforcement of "Never present speculation as fact"
- 6-point evaluation for major R&D developments
- Coverage across all 12 R&D research categories
- Extraction from SEC EDGAR XBRL company facts for R&D spending
- Extraction from OpenAlex for scientific/technical publications
- Extraction from SearXNG web search for products, patents, partnerships, etc.
- Graceful degradation and resilience when tools error or return empty data
- Synchronous and asynchronous execution
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock

from agents.rd_agent import (
    RDAgent,
    RDDiscovery,
    RDDevelopment,
    RDResearchReport,
    RESEARCH_CATEGORIES,
    EpistemicStatus,
)


class TestRDAgentSchemaAndEpistemics(unittest.TestCase):
    """Tests for schema fidelity, epistemic rules, and development QA."""

    def test_discovery_spec_dict_fields(self):
        """Verifies that to_spec_dict returns the exact 8 required fields."""
        disc = RDDiscovery(
            claim="NVIDIA launched the Blackwell GPU architecture for generative AI workloads.",
            category="New products",
            source_url="https://nvidianews.nvidia.com/news/blackwell",
            source_name="NVIDIA Press Release",
            publication_date="2025-03-18",
            company_relevance="Core flagship datacenter product line for NVIDIA Corporation.",
            potential_business_impact="Generates billions in new datacenter compute revenue with higher gross margins.",
            confidence=0.98,
            epistemic_status="FACT",
        )

        spec = disc.to_spec_dict()
        expected_keys = {
            "claim",
            "category",
            "source_url",
            "source_name",
            "publication_date",
            "company_relevance",
            "potential_business_impact",
            "confidence",
        }
        self.assertEqual(set(spec.keys()), expected_keys)
        self.assertEqual(spec["confidence"], 0.98)
        self.assertEqual(spec["category"], "New products")

    def test_epistemic_guardrail_never_presents_speculation_as_fact(self):
        """
        Enforces: If a claim contains speculative language, it must NOT remain FACT.
        It must be downgraded to SPECULATION so speculation is never presented as fact.
        """
        speculative_claims = [
            "Apple is rumored to be developing a foldable iPhone for 2026 release.",
            "Analysts speculate that Tesla might launch a robotaxi service next quarter.",
            "Unconfirmed leaks suggest a breakthrough quantum computing chip is planned.",
            "Purported roadmap indicates Microsoft could potentially acquire a gaming studio.",
        ]

        for claim in speculative_claims:
            disc = RDDiscovery(
                claim=claim,
                category="Products currently under development",
                source_url="https://tech-rumors.example.com",
                source_name="Tech Rumor Feed",
                publication_date="2026-01-15",
                company_relevance="Potential future expansion.",
                potential_business_impact="Could alter competitive market dynamics if released.",
                confidence=0.90,
                epistemic_status="FACT",  # Intentionally attempted to declare as FACT
            )

            self.assertNotEqual(
                disc.epistemic_status,
                EpistemicStatus.FACT.value,
                f"Speculative claim was improperly allowed to be FACT: '{claim}'"
            )
            self.assertEqual(disc.epistemic_status, EpistemicStatus.SPECULATION.value)
            self.assertLessEqual(disc.confidence, 0.65)

    def test_factual_claim_retains_fact_status(self):
        """A verified claim with source and factual wording retains FACT status."""
        disc = RDDiscovery(
            claim="Pfizer reported positive Phase 3 clinical trial results and received FDA approval.",
            category="Regulatory approvals or trials where relevant",
            source_url="https://fda.gov/approval",
            source_name="FDA Public Disclosure",
            publication_date="2025-11-10",
            company_relevance="Authorizes commercial distribution for Pfizer.",
            potential_business_impact="De-risks multi-billion revenue channel.",
            confidence=0.99,
            epistemic_status="FACT",
        )
        self.assertEqual(disc.epistemic_status, "FACT")

    def test_unsourced_claim_cannot_be_fact(self):
        """A claim without a source cannot be presented as a verified fact."""
        disc = RDDiscovery(
            claim="Company developed internal algorithms.",
            category="New technologies",
            source_url="",
            source_name="",
            publication_date="",
            company_relevance="Internal tool.",
            potential_business_impact="Operational efficiency.",
            confidence=0.7,
            epistemic_status="FACT",
        )
        self.assertNotEqual(disc.epistemic_status, "FACT")
        self.assertEqual(disc.epistemic_status, "INFERENCE")

    def test_all_12_categories_valid(self):
        """Verifies that all 12 research categories are properly supported and recognized."""
        self.assertEqual(len(RESEARCH_CATEGORIES), 12)
        for cat in RESEARCH_CATEGORIES:
            disc = RDDiscovery(
                claim=f"Test discovery in {cat}",
                category=cat,
                source_url="https://example.com",
                source_name="Test Source",
                publication_date="2026-01-01",
                company_relevance="Test relevance",
                potential_business_impact="Test impact",
                confidence=0.8,
            )
            self.assertEqual(disc.category, cat)

    def test_major_development_answers_all_6_questions(self):
        """
        Verifies that RDDevelopment provides clear answers to all 6 mandatory analytical questions:
        1. What is the company researching/building?
        2. How mature is it?
        3. Why does it matter?
        4. What market could it affect?
        5. What is the possible financial impact?
        6. What could prevent it from succeeding?
        """
        dev = RDDevelopment(
            title="Project Cerebrum: Custom 2nm AI Training Processor",
            category="New technologies",
            researching_building="Custom 2nm ASIC accelerator optimized for mixture-of-experts model training.",
            maturity="Laboratory Prototype / Pre-Silicon Emulation (Tape-out expected in Q3 2026).",
            why_it_matters="Reduces third-party GPU dependence and delivers 4x compute density per watt.",
            market_affected="Cloud AI training infrastructure and enterprise datacenter compute.",
            possible_financial_impact="Reduces annual capex by $1.2B while creating high-margin cloud instance tiers.",
            key_risks_or_barriers="Fabrication yield risks at leading-edge nodes, compiler software maturity, and developer switching friction.",
            epistemic_status="INFERENCE",
            supporting_sources=["https://example.com/patents/cerebrum"],
            confidence=0.88,
        )

        qa_dict = dev.to_qa_dict()
        required_questions = [
            "What is the company researching/building?",
            "How mature is it?",
            "Why does it matter?",
            "What market could it affect?",
            "What is the possible financial impact?",
            "What could prevent it from succeeding?",
        ]

        for q in required_questions:
            self.assertIn(q, qa_dict)
            self.assertTrue(len(qa_dict[q]) > 10, f"Answer for '{q}' is too short.")

        self.assertEqual(qa_dict["What is the company researching/building?"], dev.researching_building)
        self.assertEqual(qa_dict["How mature is it?"], dev.maturity)
        self.assertEqual(qa_dict["What could prevent it from succeeding?"], dev.key_risks_or_barriers)


class TestRDAgentToolIntegrations(unittest.TestCase):
    """Tests for RDAgent tool integrations with SEC, OpenAlex, and SearXNG."""

    def setUp(self):
        self.agent = RDAgent()

    def test_health_check_structure(self):
        """Verifies health check reports agent status and sub-tools without leaking keys."""
        health = self.agent.check_health()
        self.assertIn("status", health)
        self.assertIn("sub_tools", health)
        self.assertIn("sec", health["sub_tools"])
        self.assertIn("web", health["sub_tools"])
        self.assertIn("papers", health["sub_tools"])

    def test_sec_rd_spending_extraction(self):
        """Verifies extraction of GAAP R&D expense from SEC EDGAR XBRL facts."""
        mock_facts = {
            "cik": "0001045810",
            "entityName": "NVIDIA CORP",
            "facts": {
                "us-gaap": {
                    "ResearchAndDevelopmentExpense": {
                        "label": "Research and Development Expense",
                        "units": {
                            "USD": [
                                {
                                    "end": "2024-01-28",
                                    "val": 8675000000,
                                    "fy": 2024,
                                    "fp": "FY",
                                    "form": "10-K",
                                    "filed": "2024-02-21",
                                    "accn": "0001045810-24-000029",
                                },
                                {
                                    "end": "2025-01-26",
                                    "val": 12900000000,
                                    "fy": 2025,
                                    "fp": "FY",
                                    "form": "10-K",
                                    "filed": "2025-02-26",
                                    "accn": "0001045810-25-000015",
                                },
                            ]
                        },
                    }
                }
            },
        }

        with patch.object(self.agent.sec_client, "get_company_facts", return_value=mock_facts):
            spending, discoveries = asyncio.run(
                self.agent._investigate_sec_rd(
                    ticker="NVDA",
                    company_name="NVIDIA Corporation",
                    cik="0001045810",
                )
            )

            self.assertIsNotNone(spending)
            self.assertEqual(spending["latest_raw"], 12900000000)
            self.assertEqual(spending["latest_formatted"], "$12.90B")
            self.assertEqual(spending["form"], "10-K")
            self.assertEqual(spending["period_ended"], "2025-01-26")

            self.assertEqual(len(discoveries), 1)
            d = discoveries[0]
            self.assertEqual(d.category, "Company R&D spending")
            self.assertEqual(d.epistemic_status, "FACT")
            self.assertEqual(d.confidence, 1.0)
            self.assertIn("$12.90B", d.claim)

    def test_openalex_papers_extraction(self):
        """Verifies extraction of scientific/technical publications into discoveries."""
        mock_papers_response = {
            "status": "success",
            "results": [
                {
                    "title": "Megatron-LM: Training Multi-Billion Parameter Language Models",
                    "publication_year": 2020,
                    "doi": "https://doi.org/10.48550/arXiv.1909.08053",
                    "url": "https://doi.org/10.48550/arXiv.1909.08053",
                    "cited_by_count": 2150,
                    "authors": ["Mohammad Shoeybi", "Mostofa Patwary"],
                }
            ],
        }

        with patch.object(self.agent.papers_client, "search_papers", return_value=mock_papers_response):
            discoveries = asyncio.run(self.agent._investigate_papers("NVIDIA Corporation"))
            self.assertEqual(len(discoveries), 1)
            d = discoveries[0]
            self.assertEqual(d.category, "Scientific/technical publications")
            self.assertEqual(d.epistemic_status, "FACT")
            self.assertIn("Megatron-LM", d.claim)
            self.assertEqual(d.confidence, 0.95)

    def test_web_rd_category_classification(self):
        """Verifies rule-based classifier maps text to correct categories."""
        cases = [
            ("New USPTO patent granted for quantum gate interconnects", "Patents"),
            ("Company breaks ground on $4B AI datacenter gigafactory in Texas", "New factories/data centers/labs"),
            ("Firm completed acquisition of robotics AI startup Covariant", "Acquisitions"),
            ("Partnership signed with Siemens to develop industrial digital twins", "Partnerships"),
            ("Released open-source vLLM inference engine framework on GitHub", "Engineering/open-source projects"),
            ("Received FDA 510(k) clearance for medical imaging AI device", "Regulatory approvals or trials where relevant"),
            ("Breakthrough quantum computing processor architecture demonstrated", "New technologies"),
        ]

        for text, expected_cat in cases:
            classified = self.agent._classify_category(text, "New products")
            self.assertEqual(classified, expected_cat, f"Failed on: '{text}'")

    def test_end_to_end_rd_agent_run(self):
        """Verifies full end-to-end execution of RDAgent with mocked sub-tools."""
        mock_sec_spending = (
            {
                "latest_raw": 5_000_000_000,
                "latest_formatted": "$5.00B",
                "period_ended": "2025-12-31",
                "filed_date": "2026-02-15",
                "form": "10-K",
                "source_url": "https://sec.gov/filing",
            },
            [
                RDDiscovery(
                    claim="Reported $5.00B in annual R&D expenditure.",
                    category="Company R&D spending",
                    source_url="https://sec.gov/filing",
                    source_name="SEC Form 10-K",
                    publication_date="2026-02-15",
                    company_relevance="Audited US GAAP capital allocation.",
                    potential_business_impact="Drives long-term innovation moat.",
                    confidence=1.0,
                    epistemic_status="FACT",
                )
            ]
        )

        mock_paper_disc = [
            RDDiscovery(
                claim="Published research paper on distributed neural training.",
                category="Scientific/technical publications",
                source_url="https://doi.org/10.1234/test",
                source_name="OpenAlex",
                publication_date="2025",
                company_relevance="Peer-reviewed algorithm development.",
                potential_business_impact="Technical thought leadership.",
                confidence=0.95,
                epistemic_status="FACT",
            )
        ]

        mock_web_disc = [
            RDDiscovery(
                claim="Announced new H200 AI accelerator product line.",
                category="New products",
                source_url="https://news.example.com",
                source_name="Tech News",
                publication_date="2025-11-15",
                company_relevance="Commercial hardware expansion.",
                potential_business_impact="Immediate top-line acceleration.",
                confidence=0.9,
                epistemic_status="FACT",
            ),
            RDDiscovery(
                claim="Rumored to be exploring next-generation optical interconnects for 2028.",
                category="Products currently under development",
                source_url="https://rumors.example.com",
                source_name="Industry Rumors",
                publication_date="2026-01-20",
                company_relevance="Exploratory architecture research.",
                potential_business_impact="Speculative long-term bandwidth efficiency.",
                confidence=0.55,
                epistemic_status="SPECULATION",
            ),
        ]

        with patch.object(self.agent.sec_client, "get_cik", return_value=("0001234567", "TEST", "Test Tech Corp")):
            with patch.object(self.agent, "_investigate_sec_rd", return_value=mock_sec_spending):
                with patch.object(self.agent, "_investigate_papers", return_value=mock_paper_disc):
                    with patch.object(self.agent, "_investigate_web_rd", return_value=mock_web_disc):
                        report = self.agent.run("TEST")

                        self.assertIsNotNone(report)
                        self.assertIsInstance(report, RDResearchReport)
                        self.assertEqual(report.company, "Test Tech Corp")
                        self.assertEqual(report.ticker, "TEST")
                        self.assertEqual(len(report.discoveries), 4)

                        # Check category breakdown
                        self.assertIn("Company R&D spending", report.category_summary)
                        self.assertEqual(report.category_summary["Company R&D spending"], 1)
                        self.assertEqual(report.category_summary["New products"], 1)

                        # Check major developments answered 6 questions
                        self.assertGreaterEqual(len(report.major_developments), 2)
                        for dev in report.major_developments:
                            qa = dev.to_qa_dict()
                            self.assertIn("What is the company researching/building?", qa)
                            self.assertIn("How mature is it?", qa)
                            self.assertIn("Why does it matter?", qa)
                            self.assertIn("What market could it affect?", qa)
                            self.assertIn("What is the possible financial impact?", qa)
                            self.assertIn("What could prevent it from succeeding?", qa)

                        # Check prompt context and console formatting
                        prompt_ctx = report.to_prompt_context()
                        self.assertIn("R&D & TECHNOLOGY INTELLIGENCE REPORT", prompt_ctx)
                        self.assertIn("[FACT]", prompt_ctx)
                        self.assertIn("[SPECULATION]", prompt_ctx)

                        console_str = report.format_console_summary()
                        self.assertIn("R&D & TECHNOLOGY RESEARCH", console_str)

    def test_resilience_when_all_tools_raise(self):
        """Verifies that RDAgent degrades gracefully and returns a clean report even if tools fail."""
        with patch.object(self.agent.sec_client, "get_cik", return_value=None):
            with patch.object(self.agent, "_investigate_sec_rd", side_effect=Exception("SEC blocked")):
                with patch.object(self.agent, "_investigate_papers", side_effect=Exception("OpenAlex timeout")):
                    with patch.object(self.agent, "_investigate_web_rd", side_effect=Exception("SearXNG offline")):
                        report = self.agent.run("UNKNOWN_CO")

                        self.assertIsNotNone(report)
                        self.assertEqual(report.company, "UNKNOWN_CO")
                        self.assertEqual(len(report.discoveries), 0)
                        self.assertGreaterEqual(len(report.major_developments), 1)
                        # Verify fallback development has valid QA
                        dev = report.major_developments[0]
                        self.assertIn("What is the company researching/building?", dev.to_qa_dict())


if __name__ == "__main__":
    unittest.main()
