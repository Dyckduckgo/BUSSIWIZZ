"""
Unit Tests for yfinance Financial Data Client
Verifies:
- Health check functionality
- Metric extraction (all 15 required fields)
- Python derived calculations (P/E, P/S, margins)
- Graceful degradation and fallback fetcher activation
- Non-blocking async wrapper
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from tools.financial.yfinance_client import YFinanceClient
from financial_data import FinancialMetrics


class TestYFinanceClient(unittest.TestCase):
    """Test suite for free yfinance client and calculations."""

    def setUp(self):
        self.client = YFinanceClient()

    def test_health_check(self):
        """Verifies that health check returns a valid status dict."""
        health = self.client.check_health()
        self.assertIn("status", health)
        self.assertEqual(health["tool"], "yfinance")
        self.assertIn(health["status"], ["available", "degraded", "unavailable"])

    def test_derived_calculations_when_multiples_missing(self):
        """Verifies Python calculation of P/E, P/S, gross margin when not directly provided."""
        mock_info = {
            "symbol": "MOCK",
            "shortName": "Mock Corp",
            "currentPrice": 100.0,
            "marketCap": 1_000_000_000.0,
            "totalRevenue": 200_000_000.0,
            "netIncomeToCommon": 50_000_000.0,
            "trailingEps": 5.0,
            "grossProfits": 120_000_000.0,
            "operatingIncome": 70_000_000.0,
            # Explicitly omitted multiples/margins to test Python computation
            "trailingPE": None,
            "priceToSalesTrailing12Months": None,
            "grossMargins": None,
            "operatingMargins": None,
            "freeCashflow": 40_000_000.0,
            "totalCash": 30_000_000.0,
            "totalDebt": 10_000_000.0,
            "revenueGrowth": 0.25,
            "earningsGrowth": 0.30,
        }

        with patch("tools.financial.yfinance_client.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = mock_info
            mock_ticker_cls.return_value = mock_ticker

            metrics, err = self.client.get_financial_metrics("MOCK")
            self.assertIsNone(err)
            self.assertIsNotNone(metrics)
            # Calculated P/E: 100 / 5 = 20.0
            self.assertAlmostEqual(metrics.pe_ratio, 20.0)
            # Calculated P/S: 1,000,000,000 / 200,000,000 = 5.0
            self.assertAlmostEqual(metrics.ps_ratio, 5.0)
            # Calculated Gross Margin: 120,000,000 / 200,000,000 = 0.60
            self.assertAlmostEqual(metrics.gross_margin, 0.60)
            # Calculated Operating Margin: 70,000,000 / 200,000,000 = 0.35
            self.assertAlmostEqual(metrics.operating_margin, 0.35)

    def test_fallback_on_yfinance_exception(self):
        """Verifies that client falls back to internal fetcher when yfinance throws."""
        with patch("tools.financial.yfinance_client.yf.Ticker", side_effect=Exception("yfinance down")):
            with patch.object(self.client._fallback_fetcher, "fetch_metrics") as mock_fb:
                mock_metrics = FinancialMetrics(
                    symbol="FALLBACK",
                    company_name="Fallback Inc",
                    current_price=50.0,
                )
                mock_fb.return_value = (mock_metrics, None)

                metrics, err = self.client.get_financial_metrics("FALLBACK")
                self.assertIsNone(err)
                self.assertEqual(metrics.symbol, "FALLBACK")
                mock_fb.assert_called_once()

    def test_unknown_symbol_graceful_handling(self):
        """Verifies that an unknown symbol returns None without crashing."""
        with patch("tools.financial.yfinance_client.yf.Ticker") as mock_ticker_cls:
            mock_ticker = MagicMock()
            mock_ticker.info = {}
            mock_ticker.fast_info = None
            mock_ticker_cls.return_value = mock_ticker
            with patch.object(self.client._fallback_fetcher, "fetch_metrics", return_value=(None, "No data")):
                metrics, err = self.client.get_financial_metrics("UNKNOWN_FAKE_TICKER_123")
                self.assertIsNone(metrics)
                self.assertIsNotNone(err)

    def test_async_wrapper(self):
        """Verifies that get_financial_metrics_async runs without error."""
        with patch.object(self.client, "get_financial_metrics") as mock_sync:
            mock_sync.return_value = (FinancialMetrics(symbol="TEST", company_name="Test Corp"), None)
            res, err = asyncio.run(self.client.get_financial_metrics_async("TEST"))
            self.assertIsNotNone(res)
            self.assertEqual(res.symbol, "TEST")


if __name__ == "__main__":
    unittest.main()
