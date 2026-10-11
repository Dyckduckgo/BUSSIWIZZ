"""
Unit and Integration Tests for SQLite Database Storage and "What changed?" Engine
Tests:
- Database initialization and table creation (init_db, reset_db)
- Company CRUD (create_company, get_company)
- Research run creation and lifecycle (create_research_run)
- Evidence persistence and 7-verifier audit retention (save_evidence)
- Financial metrics persistence (save_metric)
- SEC filings persistence (save_filing)
- R&D findings persistence (save_rd_finding)
- Score persistence (save_score)
- Historical runs querying (get_previous_research_runs)
- "What changed?" delta engine (compare_research_runs)
"""

import unittest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db import Base, get_db_session, init_db, reset_db
from database.models import (
    Company,
    ResearchRun,
    EvidenceItem,
    FinancialMetric,
    Filing,
    NewsArticle,
    RDProject,
    ScoreRecord,
)
from database.repository import (
    ResearchRepository,
    create_company,
    get_company,
    create_research_run,
    save_evidence,
    save_metric,
    save_filing,
    save_rd_finding,
    save_score,
    get_previous_research_runs,
    compare_research_runs,
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TestDatabaseCRUDAndComparison(unittest.TestCase):
    """Tests SQLite persistence and analytical run comparison using isolated in-memory DB."""

    def setUp(self):
        # Create an isolated in-memory SQLite database for testing
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            future=True,
        )
        Base.metadata.create_all(bind=self.test_engine)
        self.TestSession = sessionmaker(bind=self.test_engine, autocommit=False, autoflush=False)
        self.session = self.TestSession()
        self.repo = ResearchRepository(session=self.session)

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(bind=self.test_engine)
        self.test_engine.dispose()

    def test_database_init_creates_all_tables(self):
        """Verifies that all 8 core tables are created cleanly on database initialization."""
        tables = Base.metadata.tables.keys()
        expected_tables = {
            "companies",
            "research_runs",
            "evidence",
            "financial_metrics",
            "filings",
            "news",
            "rd_projects",
            "scores",
        }
        self.assertTrue(expected_tables.issubset(tables))

    def test_company_crud(self):
        """Tests create_company and get_company with updates."""
        # Create
        c = self.repo.create_company(
            ticker="NVDA",
            name="NVIDIA Corporation",
            sector="Technology",
            industry="Semiconductors",
            cik="0001045810",
            session=self.session,
        )
        self.assertEqual(c.ticker, "NVDA")
        self.assertEqual(c.name, "NVIDIA Corporation")

        # Get
        fetched = self.repo.get_company("NVDA", session=self.session)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.cik, "0001045810")

        # Case insensitive lookup
        fetched_lower = self.repo.get_company("nvda", session=self.session)
        self.assertIsNotNone(fetched_lower)
        self.assertEqual(fetched_lower.id, fetched.id)

    def test_research_run_creation(self):
        """Tests create_research_run with foreign key linkage and metadata."""
        c = self.repo.create_company(ticker="AAPL", name="Apple Inc.", session=self.session)
        now = now_utc()
        run = self.repo.create_research_run(
            company_id_or_ticker=c.id,
            run_id="run_aapl_001",
            start_time=now,
            completion_time=now + timedelta(seconds=15),
            final_score=85.0,
            report_path="data/reports/AAPL_run_001.md",
            status="COMPLETED",
            session=self.session,
        )
        self.assertEqual(run.run_id, "run_aapl_001")
        self.assertEqual(run.company_ticker, "AAPL")
        self.assertEqual(run.final_score, 85.0)
        self.assertEqual(run.report_path, "data/reports/AAPL_run_001.md")

    def test_save_evidence_retains_all_fields(self):
        """Tests that evidence items retain all 9 required fields including verifier audit."""
        c = self.repo.create_company(ticker="NVDA", name="NVIDIA Corporation", session=self.session)
        run = self.repo.create_research_run(company_id_or_ticker=c.id, run_id="run_nvda_ev", session=self.session)

        now = now_utc()
        ev_item = self.repo.save_evidence(
            run_id=run.run_id,
            claim="NVIDIA gross margin expanded to 75.3% in recent filings.",
            source_url="https://sec.gov/edgar/nvda",
            source_date="2025-02-26",
            source_type="SEC_FILING",
            agent="SECAgent",
            confidence=0.99,
            verified_status=True,
            verification_reason="Verified: Supported by SEC Form 10-K as FACT with source corroboration.",
            timestamp=now,
            epistemic_status="FACT",
            category="Profitability",
            numerical_value=0.753,
            metric_name="Gross Margin",
            session=self.session,
        )

        self.assertEqual(ev_item.run_id, "run_nvda_ev")
        self.assertEqual(ev_item.agent, "SECAgent")
        self.assertTrue(ev_item.verified_status)
        self.assertIn("SEC Form 10-K", ev_item.verification_reason)
        self.assertEqual(ev_item.confidence, 0.99)
        self.assertEqual(ev_item.source_type, "SEC_FILING")
        self.assertEqual(ev_item.numerical_value, 0.753)

    def test_save_metric_and_filing_and_rd_and_score(self):
        """Tests saving metrics, filings, R&D projects, and institutional scores."""
        c = self.repo.create_company(ticker="MSFT", name="Microsoft Corporation", session=self.session)
        run = self.repo.create_research_run(company_id_or_ticker=c.id, run_id="run_msft_01", session=self.session)

        # 1. Metric
        metric = self.repo.save_metric(
            run_id=run.run_id,
            metric_name="Revenue Growth (YoY)",
            metric_value=0.155,
            metric_text="+15.5%",
            session=self.session,
        )
        self.assertEqual(metric.metric_value, 0.155)

        # 2. Filing
        filing = self.repo.save_filing(
            run_id=run.run_id,
            form_type="10-K",
            filing_date="2025-08-01",
            accession_number="0001193125-25-001234",
            source_url="https://sec.gov/Archives/msft",
            description="Annual Report",
            facts_count=45,
            session=self.session,
        )
        self.assertEqual(filing.form_type, "10-K")
        self.assertEqual(filing.facts_count, 45)

        # 3. R&D Finding
        rd = self.repo.save_rd_finding(
            run_id=run.run_id,
            title="Copilot Quantum Architecture",
            category="AI/ML developments",
            description="Distributed quantum AI inference models.",
            maturity="Research & Development",
            potential_impact="Next generation enterprise cloud computing.",
            source_url="https://microsoft.com/research",
            session=self.session,
        )
        self.assertEqual(rd.title, "Copilot Quantum Architecture")
        self.assertEqual(rd.maturity, "Research & Development")

        # 4. Score
        score = self.repo.save_score(
            run_id=run.run_id,
            total_score=89.5,
            business_quality=19.0,
            financial_health=19.0,
            growth=13.0,
            competitive_advantage=14.0,
            valuation=10.0,
            rd_innovation=9.5,
            risk_profile=5.0,
            explanation="Strong cash generation and enterprise software moat.",
            disclaimer="Disclaimer: Heuristic output.",
            session=self.session,
        )
        self.assertEqual(score.total_score, 89.5)
        self.assertEqual(run.final_score, 89.5)

    def test_compare_research_runs_what_changed(self):
        """
        Tests the "What changed?" comparative intelligence engine across two sequential runs:
        - Previous Run (Run 1):
          Revenue growth = +122.0%
          Score = 88.5
        - Current Run (Run 2):
          Revenue growth = +105.9%
          Score = 92.5
        Validates:
        - changed score & dimension deltas
        - changed financial metrics (growth slowdown)
        - new developments
        - removed/invalidated claims (rumors rejected by verifier)
        - changed risks
        - changed R&D findings
        """
        c = self.repo.create_company(ticker="NVDA", name="NVIDIA Corporation", session=self.session)

        # -------------------------------------------------------------
        # RUN 1: Previous Research Run (e.g., Q3 Cycle)
        # -------------------------------------------------------------
        t1 = now_utc() - timedelta(days=90)
        run1 = self.repo.create_research_run(
            company_id_or_ticker=c.id,
            run_id="run_nvda_q3",
            start_time=t1,
            completion_time=t1 + timedelta(seconds=20),
            final_score=88.5,
            report_path="data/reports/NVDA_run_q3.md",
            session=self.session,
        )

        self.repo.save_score(
            run_id=run1.run_id,
            total_score=88.5,
            business_quality=20.0,
            financial_health=20.0,
            growth=15.0,
            competitive_advantage=13.0,
            valuation=7.5,
            rd_innovation=8.0,
            risk_profile=5.0,
            explanation="Initial baseline research.",
            session=self.session,
        )

        self.repo.save_metric(
            run_id=run1.run_id,
            metric_name="Revenue Growth (YoY)",
            metric_value=1.22,
            metric_text="+122.0%",
            session=self.session,
        )
        self.repo.save_metric(
            run_id=run1.run_id,
            metric_name="Gross Margin",
            metric_value=0.753,
            metric_text="75.3%",
            session=self.session,
        )

        self.repo.save_evidence(
            run_id=run1.run_id,
            claim="NVIDIA Hopper GPU demand exceeds supply across hyperscalers.",
            source_name="Reuters",
            source_type="NEWS",
            agent="WebAgent",
            verified_status=True,
            verification_reason="Verified by Reuters",
            session=self.session,
        )
        self.repo.save_evidence(
            run_id=run1.run_id,
            claim="Supply chain bottlenecks at TSMC packaging facilities pose near-term risk.",
            source_name="Bloomberg",
            source_type="NEWS",
            agent="WebAgent",
            verified_status=True,
            verification_reason="Verified by Bloomberg",
            session=self.session,
        )

        self.repo.save_rd_finding(
            run_id=run1.run_id,
            title="Hopper H200 High Memory GPU",
            category="New products",
            potential_impact="Immediate datacenter upgrade cycle.",
            session=self.session,
        )

        # -------------------------------------------------------------
        # RUN 2: Current Research Run (e.g., Q4 Cycle)
        # -------------------------------------------------------------
        t2 = now_utc()
        run2 = self.repo.create_research_run(
            company_id_or_ticker=c.id,
            run_id="run_nvda_q4",
            start_time=t2,
            completion_time=t2 + timedelta(seconds=20),
            final_score=92.5,
            report_path="data/reports/NVDA_run_q4.md",
            session=self.session,
        )

        self.repo.save_score(
            run_id=run2.run_id,
            total_score=92.5,
            business_quality=20.0,
            financial_health=20.0,
            growth=15.0,
            competitive_advantage=13.0,
            valuation=9.5,  # +2.0 pt valuation multiple relief
            rd_innovation=10.0,  # +2.0 pt Blackwell rollout
            risk_profile=5.0,
            explanation="Blackwell ramp and improved valuation multiple.",
            session=self.session,
        )

        self.repo.save_metric(
            run_id=run2.run_id,
            metric_name="Revenue Growth (YoY)",
            metric_value=1.059,  # Changed from 1.22
            metric_text="+105.9%",
            session=self.session,
        )
        self.repo.save_metric(
            run_id=run2.run_id,
            metric_name="Gross Margin",
            metric_value=0.747,  # Changed from 0.753
            metric_text="74.7%",
            session=self.session,
        )

        # New verified development in Run 2
        self.repo.save_evidence(
            run_id=run2.run_id,
            claim="Blackwell Ultra AI compute platform sampling with major hyperscalers.",
            source_name="NVIDIA Official Press Release",
            source_type="OFFICIAL_PR",
            agent="RDAgent",
            verified_status=True,
            verification_reason="Verified by official press release",
            session=self.session,
        )

        # Rejected unverified rumor in Run 2
        self.repo.save_evidence(
            run_id=run2.run_id,
            claim="Unconfirmed leak blog claims next-gen consumer GPU will 10x stock price.",
            source_name="Anonymous Leak Feed",
            source_type="NEWS",
            agent="WebAgent",
            verified_status=False,
            verification_reason="Rejected: Source does not meet institutional trust threshold.",
            session=self.session,
        )

        # New risk in Run 2
        self.repo.save_evidence(
            run_id=run2.run_id,
            claim="Datacenter electrical power constraints emerging as primary deployment bottleneck.",
            source_name="WSJ",
            source_type="NEWS",
            agent="WebAgent",
            verified_status=True,
            category="risks",
            verification_reason="Verified by Wall Street Journal",
            session=self.session,
        )

        # New R&D finding in Run 2
        self.repo.save_rd_finding(
            run_id=run2.run_id,
            title="Blackwell Ultra Multi-Die Packaging",
            category="New products",
            potential_impact="Over $60B delivery backlog.",
            session=self.session,
        )

        # -------------------------------------------------------------
        # EXECUTE "WHAT CHANGED?" COMPARISON
        # -------------------------------------------------------------
        diff = self.repo.compare_research_runs(
            current_run_id=run2.run_id,
            previous_run_id=run1.run_id,
            session=self.session,
        )

        self.assertTrue(diff["has_previous_run"])
        self.assertEqual(diff["company"], "NVIDIA Corporation")
        self.assertEqual(diff["ticker"], "NVDA")

        # 1. Changed Score Check
        ch_score = diff["changed_score"]
        self.assertEqual(ch_score["previous_score"], 88.5)
        self.assertEqual(ch_score["current_score"], 92.5)
        self.assertEqual(ch_score["delta"], 4.0)
        self.assertEqual(ch_score["dimension_changes"]["Valuation (0-15)"]["delta"], 2.0)
        self.assertEqual(ch_score["dimension_changes"]["R&D / Innovation (0-10)"]["delta"], 2.0)

        # 2. Changed Financial Metrics Check
        ch_metrics = {m["metric"]: m for m in diff["changed_financial_metrics"]}
        self.assertIn("Revenue Growth (YoY)", ch_metrics)
        self.assertEqual(ch_metrics["Revenue Growth (YoY)"]["previous_text"], "+122.0%")
        self.assertEqual(ch_metrics["Revenue Growth (YoY)"]["current_text"], "+105.9%")
        self.assertEqual(ch_metrics["Revenue Growth (YoY)"]["direction"], "decreased")

        self.assertIn("Gross Margin", ch_metrics)
        self.assertEqual(ch_metrics["Gross Margin"]["previous_text"], "75.3%")
        self.assertEqual(ch_metrics["Gross Margin"]["current_text"], "74.7%")

        # 3. New Developments Check
        new_devs = [d["claim"] for d in diff["new_developments"]]
        self.assertTrue(any("Blackwell Ultra" in d for d in new_devs))

        # 4. Removed / Invalidated Claims Check
        rejected_claims = diff["removed_or_invalidated_claims"]
        self.assertTrue(any("Anonymous Leak Feed" in r.get("reason", "") or "10x stock" in r["claim"] for r in rejected_claims))

        # 5. Changed Risks Check
        risk_claims = [r["claim"] for r in diff["changed_risks"]]
        self.assertTrue(any("power constraints" in r for r in risk_claims))

        # 6. Changed R&D Findings Check
        rd_titles = [r["title"] for r in diff["changed_rd_findings"]]
        self.assertTrue(any("Blackwell Ultra" in t for t in rd_titles))

        # 7. Summary Text Check
        summary = diff["summary_text"]
        self.assertIn("What Changed: NVIDIA Corporation", summary)
        self.assertIn("+4.0 Points", summary)
        self.assertIn("+122.0% → +105.9%", summary)

    def test_get_previous_research_runs(self):
        """Tests querying historical research runs ordered by date."""
        c = self.repo.create_company(ticker="NVDA", name="NVIDIA Corporation", session=self.session)
        t_base = now_utc()
        for i in range(3):
            self.repo.create_research_run(
                company_id_or_ticker=c.id,
                run_id=f"run_nvda_hist_{i}",
                start_time=t_base + timedelta(minutes=i),
                final_score=80.0 + i,
                session=self.session,
            )

        runs = self.repo.get_previous_research_runs("NVDA", limit=5, session=self.session)
        self.assertEqual(len(runs), 3)
        # Most recent first
        self.assertEqual(runs[0].run_id, "run_nvda_hist_2")
        self.assertEqual(runs[1].run_id, "run_nvda_hist_1")
        self.assertEqual(runs[2].run_id, "run_nvda_hist_0")


if __name__ == "__main__":
    unittest.main()
