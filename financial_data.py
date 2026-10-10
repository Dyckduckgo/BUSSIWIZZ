"""
Financial Data API & Tool Module
Collects fundamental financial metrics for stocks and companies using Yahoo Finance APIs.
Performs calculations in Python for margins, valuation multiples, and growth rates.
Provides robust error handling and structured Pydantic models.
"""

import sys
import json
import urllib.parse
from typing import Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field
import requests

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_currency(val: Optional[float], currency: str = "$") -> str:
    """Formats large financial figures into human-readable currency strings (T, B, M)."""
    if val is None:
        return "N/A"
    try:
        abs_val = abs(val)
        sign = "-" if val < 0 else ""
        if abs_val >= 1e12:
            return f"{sign}{currency}{abs_val / 1e12:.2f}T"
        elif abs_val >= 1e9:
            return f"{sign}{currency}{abs_val / 1e9:.2f}B"
        elif abs_val >= 1e6:
            return f"{sign}{currency}{abs_val / 1e6:.2f}M"
        else:
            return f"{sign}{currency}{val:,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percent(val: Optional[float]) -> str:
    """Formats decimal ratios into percentage strings with sign (e.g. +14.25% or 45.10%)."""
    if val is None:
        return "N/A"
    try:
        return f"{val * 100:+.2f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_ratio(val: Optional[float]) -> str:
    """Formats valuation multiples (e.g. 24.50x)."""
    if val is None:
        return "N/A"
    try:
        return f"{val:.2f}x"
    except (ValueError, TypeError):
        return "N/A"


class FinancialMetrics(BaseModel):
    """Structured Pydantic model for company financial metrics."""
    symbol: str = Field(description="Stock ticker symbol")
    company_name: str = Field(description="Company official name")
    currency: str = Field(default="$", description="Reporting currency symbol")

    # 1. Price & Valuation
    current_price: Optional[float] = Field(default=None, description="Current stock market price")
    market_cap: Optional[float] = Field(default=None, description="Total market capitalization")
    
    # 2. Income Statement
    revenue: Optional[float] = Field(default=None, description="Total revenue (trailing twelve months)")
    net_income: Optional[float] = Field(default=None, description="Net income (TTM)")
    eps: Optional[float] = Field(default=None, description="Diluted earnings per share (TTM)")
    
    # 3. Margins
    gross_margin: Optional[float] = Field(default=None, description="Gross profit margin as decimal")
    operating_margin: Optional[float] = Field(default=None, description="Operating profit margin as decimal")
    
    # 4. Cash Flow & Balance Sheet
    free_cash_flow: Optional[float] = Field(default=None, description="Free cash flow")
    cash: Optional[float] = Field(default=None, description="Total cash and short term investments")
    debt: Optional[float] = Field(default=None, description="Total debt")
    
    # 5. Valuation Multiples
    pe_ratio: Optional[float] = Field(default=None, description="Price-to-Earnings ratio")
    ps_ratio: Optional[float] = Field(default=None, description="Price-to-Sales ratio")
    ev_ebitda: Optional[float] = Field(default=None, description="Enterprise Value to EBITDA")
    
    # 6. Growth Rates
    revenue_growth: Optional[float] = Field(default=None, description="Year-over-Year revenue growth")
    eps_growth: Optional[float] = Field(default=None, description="Year-over-Year EPS / earnings growth")

    def to_summary_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary with both raw and formatted values."""
        return {
            "Symbol": self.symbol,
            "Company Name": self.company_name,
            "Current Price": format_currency(self.current_price, self.currency),
            "Market Cap": format_currency(self.market_cap, self.currency),
            "Revenue (TTM)": format_currency(self.revenue, self.currency),
            "Net Income (TTM)": format_currency(self.net_income, self.currency),
            "Diluted EPS": format_currency(self.eps, self.currency),
            "Gross Margin": format_percent(self.gross_margin),
            "Operating Margin": format_percent(self.operating_margin),
            "Free Cash Flow": format_currency(self.free_cash_flow, self.currency),
            "Total Cash": format_currency(self.cash, self.currency),
            "Total Debt": format_currency(self.debt, self.currency),
            "P/E Ratio": format_ratio(self.pe_ratio),
            "P/S Ratio": format_ratio(self.ps_ratio),
            "EV/EBITDA": format_ratio(self.ev_ebitda),
            "Revenue Growth (YoY)": format_percent(self.revenue_growth),
            "EPS Growth (YoY)": format_percent(self.eps_growth),
        }

    def format_table(self) -> str:
        """Formats the 15 metrics into a clean, aligned ASCII table."""
        summary = self.to_summary_dict()
        title = f"FINANCIAL METRICS SUMMARY: {self.company_name} ({self.symbol})"
        width = 68
        border = "+" + "-" * (width - 2) + "+"
        div = "+" + "-" * 34 + "+" + "-" * 31 + "+"

        lines = [
            border,
            f"| {title.center(width - 4)} |",
            border,
            f"| {'Metric'.ljust(32)} | {'Value'.ljust(29)} |",
            div,
        ]

        for metric, val in summary.items():
            if metric in ("Symbol", "Company Name"):
                continue
            lines.append(f"| {metric.ljust(32)} | {str(val).ljust(29)} |")

        lines.append(border)
        return "\n".join(lines)


class FinancialDataFetcher:
    """Robust client to query and calculate financial data from public market feeds."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        })
        self._crumb: Optional[str] = None

    def _get_crumb(self) -> Optional[str]:
        """Obtains session cookie and authentication crumb token from Yahoo Finance."""
        if self._crumb:
            return self._crumb

        try:
            # Initialize session cookie
            self.session.get("https://fc.yahoo.com", timeout=8)
            # Retrieve crumb
            crumb_resp = self.session.get("https://query2.finance.yahoo.com/v1/test/getcrumb", timeout=8)
            if crumb_resp.status_code == 200 and crumb_resp.text:
                self._crumb = crumb_resp.text.strip()
                return self._crumb
        except Exception:
            pass
        return None

    def resolve_ticker(self, query: str) -> Tuple[str, str]:
        """
        Resolves a company name or ticker query to an official ticker symbol and name.
        Example: 'Microsoft' -> ('MSFT', 'Microsoft Corporation')
        """
        clean_query = query.strip()
        try:
            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(clean_query)}"
            resp = self.session.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                quotes = data.get("quotes", [])
                for q in quotes:
                    if q.get("quoteType") in ("EQUITY", "ETF"):
                        symbol = q.get("symbol", clean_query.upper())
                        name = q.get("shortname") or q.get("longname") or clean_query
                        return symbol, name
                if quotes:
                    symbol = quotes[0].get("symbol", clean_query.upper())
                    name = quotes[0].get("shortname") or quotes[0].get("longname") or clean_query
                    return symbol, name
        except Exception:
            pass

        return clean_query.upper(), clean_query

    def fetch_metrics(self, query: str) -> Tuple[Optional[FinancialMetrics], Optional[str]]:
        """
        Retrieves real-time financial stats for a given company name or ticker.
        Performs Python calculations for missing ratios or margins.
        Returns (FinancialMetrics, None) on success, or (None, error_message) on failure.
        """
        symbol, company_name = self.resolve_ticker(query)

        crumb = self._get_crumb()
        modules = "price,financialData,defaultKeyStatistics,summaryDetail"
        quote_url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{urllib.parse.quote(symbol)}"
        params = {"modules": modules}
        if crumb:
            params["crumb"] = crumb

        try:
            response = self.session.get(quote_url, params=params, timeout=10)
        except requests.exceptions.Timeout:
            return None, f"Timeout connecting to financial data service for '{symbol}'."
        except requests.exceptions.RequestException as e:
            return None, f"Network connection error while fetching financial data: {str(e)}"

        if response.status_code != 200:
            # Fallback attempt via chart API if quoteSummary is restricted
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
            try:
                chart_resp = self.session.get(chart_url, timeout=8)
                if chart_resp.status_code == 200:
                    c_data = chart_resp.json().get("chart", {}).get("result", [{}])[0]
                    meta = c_data.get("meta", {})
                    curr_price = meta.get("regularMarketPrice")
                    currency = meta.get("currencySymbol") or "$"
                    if curr_price:
                        # Return partial metrics
                        return FinancialMetrics(
                            symbol=symbol,
                            company_name=company_name,
                            currency=currency,
                            current_price=curr_price,
                        ), f"Partial data: Complete financial modules unavailable (HTTP {response.status_code}), retrieved live price."
            except Exception:
                pass
            return None, f"Financial data API returned status code {response.status_code} for '{symbol}'."

        try:
            res_json = response.json()
            result_list = res_json.get("quoteSummary", {}).get("result")
            if not result_list:
                return None, f"No financial summary data found for '{symbol}'."
            data = result_list[0]
        except (ValueError, KeyError) as json_err:
            return None, f"Failed to parse financial data response: {str(json_err)}"

        fd = data.get("financialData", {})
        ks = data.get("defaultKeyStatistics", {})
        p = data.get("price", {})
        sd = data.get("summaryDetail", {})

        def extract_raw(container: Dict[str, Any], key: str) -> Optional[float]:
            """Extracts raw numerical value from Yahoo Finance dictionaries."""
            val = container.get(key)
            if isinstance(val, dict) and "raw" in val:
                return val["raw"]
            if isinstance(val, (int, float)):
                return float(val)
            return None

        # 1. Price & Market Cap
        current_price = extract_raw(p, "regularMarketPrice") or extract_raw(fd, "currentPrice")
        market_cap = extract_raw(p, "marketCap") or extract_raw(sd, "marketCap")
        currency = p.get("currencySymbol") or "$"

        # 2. Revenue & Profits
        revenue = extract_raw(fd, "totalRevenue")
        net_income = extract_raw(ks, "netIncomeToCommon")
        eps = extract_raw(ks, "trailingEps")

        # 3. Margins (Use Python calculation if raw margin is missing)
        gross_margin = extract_raw(fd, "grossMargins")
        if gross_margin is None:
            gross_profits = extract_raw(fd, "grossProfits")
            if gross_profits is not None and revenue and revenue > 0:
                gross_margin = gross_profits / revenue

        operating_margin = extract_raw(fd, "operatingMargins")
        if operating_margin is None:
            ebit = extract_raw(fd, "ebitda")
            if ebit is not None and revenue and revenue > 0:
                operating_margin = ebit / revenue

        # 4. Cash Flow, Cash & Debt
        free_cash_flow = extract_raw(fd, "freeCashflow")
        cash = extract_raw(fd, "totalCash")
        debt = extract_raw(fd, "totalDebt")

        # 5. Valuation Multiples (Use Python calculation when appropriate)
        pe_ratio = extract_raw(sd, "trailingPE")
        if pe_ratio is None and current_price is not None and eps is not None and eps > 0:
            pe_ratio = current_price / eps

        ps_ratio = extract_raw(sd, "priceToSalesTrailing12Months")
        if ps_ratio is None and market_cap is not None and revenue is not None and revenue > 0:
            ps_ratio = market_cap / revenue

        ev_ebitda = extract_raw(ks, "enterpriseToEbitda")
        if ev_ebitda is None:
            enterprise_val = extract_raw(ks, "enterpriseValue")
            ebitda_val = extract_raw(fd, "ebitda")
            if enterprise_val is not None and ebitda_val is not None and ebitda_val > 0:
                ev_ebitda = enterprise_val / ebitda_val

        # 6. Growth Rates
        revenue_growth = extract_raw(fd, "revenueGrowth") or extract_raw(ks, "revenueQuarterlyGrowth")
        eps_growth = extract_raw(fd, "earningsGrowth") or extract_raw(ks, "earningsQuarterlyGrowth")

        metrics = FinancialMetrics(
            symbol=symbol,
            company_name=company_name,
            currency=currency,
            current_price=current_price,
            market_cap=market_cap,
            revenue=revenue,
            net_income=net_income,
            eps=eps,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            free_cash_flow=free_cash_flow,
            cash=cash,
            debt=debt,
            pe_ratio=pe_ratio,
            ps_ratio=ps_ratio,
            ev_ebitda=ev_ebitda,
            revenue_growth=revenue_growth,
            eps_growth=eps_growth,
        )

        return metrics, None


# Singleton instance
_fetcher = FinancialDataFetcher()


def fetch_financial_data(query: str) -> Tuple[Optional[FinancialMetrics], Optional[str]]:
    """Public helper function to fetch financial metrics."""
    return _fetcher.fetch_metrics(query)
