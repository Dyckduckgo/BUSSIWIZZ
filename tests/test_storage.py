"""
Unit Tests for SQLite Storage Layer
Verifies:
- Table initialization
- Health check
- Session saving and retrieval
- Foreign key data integrity (financials, SEC facts, web sources)
"""

import os
import unittest
import tempfile
from storage.db import Database


class TestDatabaseStorage(unittest.TestCase):
    """Test suite for SQLite storage manager."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_research.db")
        self.db = Database(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_check(self):
        """Verifies database connectivity check."""
        health = self.db.check_health()
        self.assertEqual(health["status"], "healthy")
        self.assertEqual(health["path"], self.db_path)

    def test_save_and_retrieve_session(self):
        """Verifies full session storage and retrieval."""
        session_id = "test_session_123"
        company = "NVIDIA Corporation"
        ticker = "NVDA"

        fin_data = {
            "current_price": 230.50,
            "market_cap": 5_600_000_000_000.0,
            "revenue": 300_000_000_000.0,
            "net_income": 190_000_000_000.0,
            "eps": 7.80,
            "pe_ratio": 29.5,
            "ps_ratio": 18.6,
            "ev_ebitda": 27.5,
            "gross_margin": 0.75,
            "operating_margin": 0.66,
            "free_cash_flow": 41_000_000_000.0,
            "cash": 62_000_000_000.0,
            "debt": 38_000_000_000.0,
            "revenue_growth": 1.05,
            "eps_growth": 1.25,
            "data_source": "yfinance",
        }

        sec_facts = [
            {
                "claim": "Revenues",
                "value": "$30.04B",
                "filing_type": "10-Q",
                "filing_date": "2026-08-28",
                "accession_number": "0001045810-26-000075",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/...",
                "snippet": "Three months ended July 28, 2026 revenue was $30,040 million.",
            }
        ]

        web_sources = [
            {
                "title": "NVIDIA Q2 Results",
                "url": "https://nvidianews.nvidia.com/news/...",
                "snippet": "NVIDIA reports Q2 revenue of $30.0 billion.",
                "engine": "searxng_mcp",
            }
        ]

        self.db.save_session(
            session_id=session_id,
            company=company,
            ticker=ticker,
            status="completed",
            model_used="openai/gpt-oss-120b",
            full_report="## 1. Company Overview\nNVIDIA is...",
            financial_metrics=fin_data,
            sec_facts=sec_facts,
            web_sources=web_sources,
        )

        retrieved = self.db.get_session_by_id(session_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["company"], company)
        self.assertEqual(retrieved["ticker"], ticker)
        self.assertEqual(retrieved["model_used"], "openai/gpt-oss-120b")

        # Verify financials
        fin = retrieved.get("financial_snapshot")
        self.assertIsNotNone(fin)
        self.assertEqual(fin["current_price"], 230.50)
        self.assertEqual(fin["pe_ratio"], 29.5)

        # Verify SEC facts
        facts = retrieved.get("sec_facts", [])
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["claim"], "Revenues")
        self.assertEqual(facts[0]["value"], "$30.04B")

        # Verify Web sources
        sources = retrieved.get("web_sources", [])
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "NVIDIA Q2 Results")

    def test_recent_sessions_listing(self):
        """Verifies order and count of recent sessions list."""
        for i in range(5):
            self.db.save_session(
                session_id=f"sess_{i}",
                company=f"Company {i}",
                ticker=f"TICK{i}",
                status="completed",
                model_used="local_synthesis",
                full_report="Report",
            )

        recent = self.db.get_recent_sessions(limit=3)
        self.assertEqual(len(recent), 3)
        # Should be ordered DESC by id (sess_4 first)
        self.assertEqual(recent[0]["session_id"], "sess_4")


if __name__ == "__main__":
    unittest.main()
