"""
yfinance Financial Client
Fetches market prices, valuation multiples, and fundamental metrics using yfinance.
Features:
- Collects all 15 required metrics.
- Performs Python calculations for missing multiples and ratios.
- Health check to monitor Yahoo Finance / yfinance API status.
- Automatic fallback to internal FinancialDataFetcher if yfinance fails.
- Async execution wrapper for non-blocking concurrent research.
"""

import os
import sys
import asyncio
from typing import Optional, Dict, Any, Tuple
import yfinance as yf

# Import existing working models and fallback fetcher to preserve functionality
from financial_data import FinancialMetrics, FinancialDataFetcher


class YFinanceClient:
    """Zero-paid-key financial metrics client backed by yfinance with direct fallback."""

    def __init__(self):
        self._fallback_fetcher = FinancialDataFetcher()

    def check_health(self) -> Dict[str, Any]:
        """
        Verifies yfinance connectivity by checking a test symbol.
        Returns health status dictionary.
        """
        try:
            ticker = yf.Ticker("SPY")
            # fast_info has minimal overhead
            price = getattr(ticker.fast_info, "last_price", None)
            if price is not None and price > 0:
                return {
                    "status": "available",
                    "tool": "yfinance",
                    "active_mode": "yfinance",
                    "message": "yfinance market feed is healthy and responsive.",
                }
            return {
                "status": "degraded",
                "tool": "yfinance",
                "active_mode": "fallback_fetcher",
                "message": "yfinance returned empty price, fallback fetcher active.",
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "tool": "yfinance",
                "active_mode": "fallback_fetcher",
                "message": f"yfinance error: {type(e).__name__}. Fallback fetcher active.",
            }

    def resolve_ticker(self, query: str) -> Tuple[str, str]:
        """Resolves company name or symbol to (ticker, company_name)."""
        return self._fallback_fetcher.resolve_ticker(query)

    def get_financial_metrics(self, company_or_ticker: str) -> Tuple[Optional[FinancialMetrics], Optional[str]]:
        """
        Retrieves real-time and fundamental financial metrics for a company or ticker symbol.
        Returns (FinancialMetrics, None) on success or (None, error_msg) if completely unavailable.
        """
        symbol, company_name = self.resolve_ticker(company_or_ticker)

        # 1. Primary Attempt: yfinance
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            fast_info = getattr(ticker, "fast_info", None)

            # Price & Market Cap
            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or getattr(fast_info, "last_price", None)
            )
            market_cap = (
                info.get("marketCap")
                or getattr(fast_info, "market_cap", None)
            )

            # Financial Statements
            revenue = info.get("totalRevenue")
            net_income = info.get("netIncomeToCommon") or info.get("netIncome")
            eps = info.get("trailingEps")

            # Margins
            gross_margin = info.get("grossMargins")
            operating_margin = info.get("operatingMargins")

            # Cash Flow & Balance Sheet
            free_cash_flow = info.get("freeCashflow")
            cash = info.get("totalCash")
            debt = info.get("totalDebt")

            # Valuation Multiples
            pe_ratio = info.get("trailingPE")
            ps_ratio = info.get("priceToSalesTrailing12Months")
            ev_ebitda = info.get("enterpriseToEbitda")

            # Growth Rates
            revenue_growth = info.get("revenueGrowth")
            eps_growth = info.get("earningsGrowth")

            currency = info.get("currency", "$")
            resolved_name = info.get("shortName") or info.get("longName") or company_name

            # Python Calculations for Missing Multiples/Margins
            if gross_margin is None and revenue and info.get("grossProfits"):
                gross_margin = info["grossProfits"] / revenue

            if operating_margin is None and revenue and info.get("operatingIncome"):
                operating_margin = info["operatingIncome"] / revenue

            if pe_ratio is None and price and eps and eps > 0:
                pe_ratio = price / eps

            if ps_ratio is None and market_cap and revenue and revenue > 0:
                ps_ratio = market_cap / revenue

            # If yfinance returned a valid price or revenue, return the metrics
            if price is not None or revenue is not None or market_cap is not None:
                metrics = FinancialMetrics(
                    symbol=symbol,
                    company_name=resolved_name,
                    currency=currency if currency != "USD" else "$",
                    current_price=float(price) if price is not None else None,
                    market_cap=float(market_cap) if market_cap is not None else None,
                    revenue=float(revenue) if revenue is not None else None,
                    net_income=float(net_income) if net_income is not None else None,
                    eps=float(eps) if eps is not None else None,
                    gross_margin=float(gross_margin) if gross_margin is not None else None,
                    operating_margin=float(operating_margin) if operating_margin is not None else None,
                    free_cash_flow=float(free_cash_flow) if free_cash_flow is not None else None,
                    cash=float(cash) if cash is not None else None,
                    debt=float(debt) if debt is not None else None,
                    pe_ratio=float(pe_ratio) if pe_ratio is not None else None,
                    ps_ratio=float(ps_ratio) if ps_ratio is not None else None,
                    ev_ebitda=float(ev_ebitda) if ev_ebitda is not None else None,
                    revenue_growth=float(revenue_growth) if revenue_growth is not None else None,
                    eps_growth=float(eps_growth) if eps_growth is not None else None,
                )
                return metrics, None

        except Exception as yf_err:
            # yfinance failed, proceed to fallback fetcher
            pass

        # 2. Secondary Attempt: Fallback session fetcher
        try:
            metrics, err = self._fallback_fetcher.fetch_metrics(symbol)
            if metrics:
                return metrics, None
            return None, err or "Financial data unavailable from both primary and fallback sources."
        except Exception as fb_err:
            return None, f"Financial data fetch error: {str(fb_err)}"

    async def get_financial_metrics_async(self, company_or_ticker: str) -> Tuple[Optional[FinancialMetrics], Optional[str]]:
        """Non-blocking asynchronous wrapper for fetching financial metrics."""
        return await asyncio.to_thread(self.get_financial_metrics, company_or_ticker)
