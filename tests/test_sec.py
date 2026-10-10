"""
Unit tests for SEC EDGAR Research Tool:
- CIK lookup
- Filing lookup
- Missing data handling
- Malformed API responses handling
"""

import unittest
from unittest.mock import MagicMock, patch

from tools.sec.sec_client import SECClient
from tools.sec.sec_parser import (
    SECParser,
    SECExtractedFact,
    SECFilingMeta,
    SECInsiderTransaction,
)
from agents.sec_agent import SECAgent, SECResearchReport


class TestCIKLookup(unittest.TestCase):
    """Tests for company name / ticker to CIK lookup functionality."""

    def setUp(self):
        self.client = SECClient()
        # Mock cached tickers data for deterministic isolated testing
        self.mock_tickers = {
            "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
            "1": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "2": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
        }
        self.client._tickers_cache = self.mock_tickers

    def test_exact_ticker_lookup(self):
        res = self.client.get_cik("NVDA")
        self.assertIsNotNone(res)
        cik, ticker, title = res
        self.assertEqual(cik, "0001045810")
        self.assertEqual(ticker, "NVDA")
        self.assertEqual(title, "NVIDIA CORP")

    def test_case_insensitive_lookup(self):
        res = self.client.get_cik("aapl")
        self.assertIsNotNone(res)
        cik, ticker, title = res
        self.assertEqual(cik, "0000320193")
        self.assertEqual(ticker, "AAPL")

    def test_title_substring_lookup(self):
        res = self.client.get_cik("Microsoft")
        self.assertIsNotNone(res)
        cik, ticker, title = res
        self.assertEqual(cik, "0000789019")
        self.assertEqual(ticker, "MSFT")

    def test_cik_zero_padding(self):
        res = self.client.get_cik("AAPL")
        self.assertIsNotNone(res)
        cik = res[0]
        self.assertEqual(len(cik), 10)
        self.assertTrue(cik.isdigit())


class TestFilingLookup(unittest.TestCase):
    """Tests for parsing and filtering recent SEC filings."""

    def setUp(self):
        self.client = SECClient()
        self.mock_submissions = {
            "filings": {
                "recent": {
                    "form": ["10-K", "10-Q", "8-K", "4", "20-F", "10-Q"],
                    "filingDate": ["2026-02-25", "2026-08-26", "2026-09-03", "2026-09-21", "2026-04-15", "2026-05-20"],
                    "reportDate": ["2026-01-25", "2026-07-26", "2026-09-02", "2026-09-20", "2026-03-31", "2026-04-26"],
                    "accessionNumber": [
                        "0001045810-26-000021",
                        "0001045810-26-000075",
                        "0001045810-26-000078",
                        "0001696841-26-000014",
                        "0001193125-26-000099",
                        "0001045810-26-000052",
                    ],
                    "primaryDocument": [
                        "nvda-20260125.htm",
                        "nvda-20260726.htm",
                        "nvda-20260902.htm",
                        "wk-form4_1790196985.xml",
                        "form20f.htm",
                        "nvda-20260426.htm",
                    ],
                    "primaryDocDescription": ["10-K", "10-Q", "8-K", "4", "20-F", "10-Q"],
                }
            }
        }

    def test_filing_grouping_by_form(self):
        filings = SECParser.parse_recent_filings(self.mock_submissions, "0001045810", self.client)
        self.assertEqual(len(filings["10-K"]), 1)
        self.assertEqual(len(filings["10-Q"]), 2)
        self.assertEqual(len(filings["8-K"]), 1)
        self.assertEqual(len(filings["4"]), 1)
        self.assertEqual(len(filings["20-F"]), 1)

    def test_document_url_generation(self):
        filings = SECParser.parse_recent_filings(self.mock_submissions, "0001045810", self.client)
        item_10q = filings["10-Q"][0]
        self.assertIn("https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm", item_10q.source_url)
        self.assertEqual(item_10q.filing_date, "2026-08-26")


class TestMissingData(unittest.TestCase):
    """Tests behavior when data is missing, non-existent, or empty."""

    def setUp(self):
        self.client = SECClient()
        self.client._tickers_cache = {
            "0": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"}
        }

    def test_nonexistent_ticker_returns_none(self):
        res = self.client.get_cik("NONEXISTENT_XYZ_123")
        self.assertIsNone(res)

    def test_empty_submissions_returns_empty_dict(self):
        filings = SECParser.parse_recent_filings({}, "0001045810", self.client)
        self.assertIsInstance(filings, dict)
        for form in ("10-K", "10-Q", "8-K", "4", "20-F"):
            self.assertEqual(filings[form], [])

    def test_missing_gaap_facts(self):
        empty_facts = {"facts": {}}
        facts, summary = SECParser.parse_xbrl_facts(empty_facts, "0001045810", "NVDA", "NVIDIA CORP", self.client)
        self.assertEqual(facts, [])
        self.assertEqual(summary, {})

    def test_empty_form4_xml(self):
        trades = SECParser.parse_form4_xml("", "0001045810", "0001", "2026-09-01", "NVDA", "NVIDIA CORP", "http://example.com")
        self.assertEqual(trades, [])


class TestMalformedAPIResponses(unittest.TestCase):
    """Tests resilience against corrupted or malformed API payloads."""

    def setUp(self):
        self.client = SECClient()

    def test_malformed_submissions_structure(self):
        # submissions missing recent lists or containing non-list types
        corrupted_sub = {
            "filings": {
                "recent": {
                    "form": "invalid_string_not_list",
                    "filingDate": None,
                }
            }
        }
        filings = SECParser.parse_recent_filings(corrupted_sub, "0001045810", self.client)
        self.assertEqual(filings["10-K"], [])

    def test_corrupted_company_facts_structure(self):
        # concepts with unexpected units structure
        corrupted_facts = {
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": "not_a_dict"
                    },
                    "NetIncomeLoss": {
                        "units": {
                            "USD": [{"val": "invalid_number_string", "form": "10-Q", "filed": "2026-08-01"}]
                        }
                    }
                }
            }
        }
        # Should not throw exception
        facts, summary = SECParser.parse_xbrl_facts(corrupted_facts, "0001045810", "NVDA", "NVIDIA CORP", self.client)
        self.assertIsInstance(facts, list)

    def test_malformed_form4_xml(self):
        bad_xml = "<ownershipDocument><broken><unclosed>"
        trades = SECParser.parse_form4_xml(bad_xml, "0001045810", "0001", "2026-09-01", "NVDA", "NVIDIA CORP", "http://example.com")
        self.assertEqual(trades, [])

    def test_agent_graceful_handling_when_cik_not_found(self):
        agent = SECAgent(client=self.client)
        with patch.object(self.client, "get_cik", return_value=None):
            report = agent.run("FOREIGN_PRIVATE_COMPANY")
            self.assertIsNone(report)


if __name__ == "__main__":
    unittest.main()
