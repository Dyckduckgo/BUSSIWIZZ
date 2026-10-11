"""
Financial Research Agent
Autonomous specialist agent for equity fundamentals, market pricing,
margins, capital structure, and growth rates. Produces structured Evidence objects.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple

from tools.financial.yfinance_client import YFinanceClient
from financial_data import FinancialMetrics, format_currency, format_percent, format_ratio
from agents.models import Evidence

logger = logging.getLogger("agents.financial_agent")


class FinancialAgent:
    """Specialist agent for quantitative financial analysis and metric evidence."""

    def __init__(self, yfinance_client: Optional[YFinanceClient] = None):
        self.client = yfinance_client or YFinanceClient()

    def check_health(self) -> Dict[str, Any]:
        """Health check for financial feeds."""
        h = self.client.check_health()
        return {
            "status": h.get("status", "available"),
            "tool": "financial_agent",
            "active_mode": h.get("active_mode", "yfinance_api"),
            "message": h.get("message", "Financial data agent ready."),
        }

    async def run_async(self, company_or_ticker: str) -> Tuple[Optional[FinancialMetrics], List[Evidence]]:
        """
        Retrieves real-time market metrics and fundamental financial ratios.
        Converts every verified numerical metric into a structured Evidence item.
        """
        logger.info(f"[FinancialAgent] Querying financial metrics for '{company_or_ticker}' via yfinance")
        clean_target = company_or_ticker.strip()
        metrics, err = await self.client.get_financial_metrics_async(clean_target)

        evidence_list: List[Evidence] = []
        if not metrics:
            logger.warning(f"[FinancialAgent] Failed to retrieve metrics for {clean_target}: {err}")
            return None, evidence_list

        source_url = f"https://finance.yahoo.com/quote/{metrics.symbol}"
        source_name = "Yahoo Finance API / Market Data Feed"
        source_date = "Current Market Data"

        # Map each critical quantitative dimension into verifiable evidence
        def add_metric_ev(name: str, val: Optional[float], formatted_str: str, desc: str):
            if val is not None:
                ev = Evidence(
                    claim=f"{metrics.company_name} ({metrics.symbol}) {name} is {formatted_str}.",
                    source_url=source_url,
                    source_name=source_name,
                    source_date=source_date,
                    source_type="FINANCIAL_API",
                    evidence_text=f"Reported {name}: {formatted_str} ({desc}).",
                    confidence=0.98,
                    agent_name="FinancialAgent",
                    epistemic_status="FACT",
                    numerical_value=float(val),
                    metric_name=name,
                )
                evidence_list.append(ev)

        summary = metrics.to_summary_dict()

        add_metric_ev("Current Stock Price", metrics.current_price, summary.get("Current Price", "N/A"), "Market regular session price")
        add_metric_ev("Market Capitalization", metrics.market_cap, summary.get("Market Cap", "N/A"), "Total equity market valuation")
        add_metric_ev("Total Revenue (TTM)", metrics.revenue, summary.get("Revenue (TTM)", "N/A"), "Trailing twelve months aggregate revenue")
        add_metric_ev("Net Income (TTM)", metrics.net_income, summary.get("Net Income (TTM)", "N/A"), "GAAP net profit after tax")
        add_metric_ev("Diluted EPS", metrics.eps, summary.get("Diluted EPS", "N/A"), "Diluted earnings per share")
        add_metric_ev("Gross Margin", metrics.gross_margin, summary.get("Gross Margin", "N/A"), "Gross profit as percentage of revenue")
        add_metric_ev("Operating Margin", metrics.operating_margin, summary.get("Operating Margin", "N/A"), "Operating income as percentage of revenue")
        add_metric_ev("Free Cash Flow", metrics.free_cash_flow, summary.get("Free Cash Flow", "N/A"), "Operating cash flow less capital expenditures")
        add_metric_ev("Total Cash and Short-term Investments", metrics.cash, summary.get("Total Cash", "N/A"), "Balance sheet liquid reserves")
        add_metric_ev("Total Debt", metrics.debt, summary.get("Total Debt", "N/A"), "Total short and long term liabilities")
        add_metric_ev("Price-to-Earnings Ratio", metrics.pe_ratio, summary.get("P/E Ratio", "N/A"), "Trailing price-to-earnings valuation multiple")
        add_metric_ev("Price-to-Sales Ratio", metrics.ps_ratio, summary.get("P/S Ratio", "N/A"), "Price-to-sales valuation multiple")
        add_metric_ev("EV/EBITDA Multiple", metrics.ev_ebitda, summary.get("EV/EBITDA", "N/A"), "Enterprise value to EBITDA multiple")
        add_metric_ev("Revenue Growth (YoY)", metrics.revenue_growth, summary.get("Revenue Growth (YoY)", "N/A"), "Year-over-year revenue expansion rate")
        add_metric_ev("Earnings Growth (YoY)", metrics.eps_growth, summary.get("EPS Growth (YoY)", "N/A"), "Year-over-year earnings growth rate")

        logger.info(f"[FinancialAgent] Extracted {len(evidence_list)} quantitative evidence points for {metrics.symbol}.")
        return metrics, evidence_list

    def run(self, company_or_ticker: str) -> Tuple[Optional[FinancialMetrics], List[Evidence]]:
        """Synchronous wrapper for run_async."""
        import asyncio
        return asyncio.run(self.run_async(company_or_ticker))
