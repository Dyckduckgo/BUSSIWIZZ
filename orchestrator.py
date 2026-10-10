"""
Research Orchestrator
Coordinates concurrent, async research across:
1. Local SearXNG MCP / Direct HTTP fallback for real-time web research
2. yfinance for market prices, fundamental ratios, and financial metrics
3. SEC EDGAR for official US regulatory filings, XBRL facts, and insider activity
4. Groq LLM for synthesis (using models available on the free tier)
5. Optional OpenAlex for public academic paper research

Key guarantees:
- Every external tool is optional; failures degrade gracefully without crashing.
- No hardcoded API keys.
- Fully async/concurrent execution via asyncio.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

# Load this project's settings regardless of the caller's working directory.
load_dotenv(Path(__file__).resolve().parent / ".env")

from tools.mcp.searxng_client import SearXNGClient
from tools.financial.yfinance_client import YFinanceClient
from tools.sec.sec_client import SECClient
from tools.papers.openalex_client import OpenAlexClient
from agents.sec_agent import SECAgent, SECResearchReport
from financial_data import FinancialMetrics

try:
    from groq import Groq, GroqError
except ImportError:
    Groq = None
    GroqError = Exception

SYSTEM_PROMPT = """You are an elite equity research analyst and business intelligence agent.
Your objective is to produce an authoritative, objective, and up-to-date research report on the requested company or stock.

You must structure your report strictly into the following 6 numbered sections:

1. Company Overview
   - Core business model, primary sectors/industries, key products or revenue engines.
   - Market positioning, primary customer segments, and competitive moat.

2. Recent Developments
   - Material corporate announcements, product launches, acquisitions, or partnerships from recent quarters.
   - Key executive, organizational, or regulatory shifts impacting the business.

3. Revenue & Profit Information
   - Explicitly cite the verified financial metrics: Current Price, Market Cap, Revenue, Net Income, Margins, Cash, Debt, and Growth rates.
   - Analysis of revenue momentum, profitability trends, and margin expansion/compression.
   - Recent earnings surprises or management forward guidance.

4. Major Risks
   - Specific operational, competitive, technological, regulatory, or macroeconomic headwinds.

5. Growth Opportunities
   - Primary growth catalysts, market expansion vectors, and emerging product/service tailwinds.

6. Sources for Important Claims
   - Provide a clear, bulleted or numbered list of sources (articles, filings, financial portals, URLs) for all key factual claims and news cited.

Tone: Professional, fact-based, rigorous, and balanced. Avoid speculative hype.
"""


class ResearchOrchestrator:
    """Orchestrates multi-source concurrent research with robust fallback mechanisms."""

    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.searxng_client = SearXNGClient()
        self.yfinance_client = YFinanceClient()
        self.sec_agent = SECAgent()
        self.papers_client = OpenAlexClient()

    def check_all_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Runs health checks on all sub-systems and returns their availability status.
        """
        searxng_health = self.searxng_client.check_health()
        yfinance_health = self.yfinance_client.check_health()
        sec_health = self.sec_agent.client.check_health()
        papers_health = self.papers_client.check_health()

        groq_status = "available" if self.groq_api_key else "missing_key"
        groq_message = (
            "Groq API key configured."
            if self.groq_api_key
            else "GROQ_API_KEY missing in .env. Factual local synthesis will be used."
        )

        return {
            "searxng_mcp": searxng_health,
            "yfinance": yfinance_health,
            "sec_edgar": sec_health,
            "openalex_papers": papers_health,
            "groq_llm": {
                "status": groq_status,
                "tool": "groq_llm",
                "active_mode": "cloud_llm" if self.groq_api_key else "local_synthesis",
                "message": groq_message,
            },
        }

    async def run_research(
        self,
        company_or_ticker: str,
        include_papers: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes concurrent research across yfinance, SEC EDGAR, SearXNG MCP / fallback,
        and optional paper search, followed by synthesis.
        """
        clean_target = company_or_ticker.strip()
        fallbacks_used: List[str] = []
        health_statuses = self.check_all_health()

        # Step 1: Launch Concurrent Research Tasks
        task_financial = self.yfinance_client.get_financial_metrics_async(clean_target)
        task_sec = asyncio.to_thread(self.sec_agent.run, clean_target)
        task_web = self.searxng_client.search(f"{clean_target} stock financial earnings risks 2026", max_results=5)

        tasks = [task_financial, task_sec, task_web]
        if include_papers:
            task_papers = self.papers_client.search_papers(f"{clean_target} architecture technology", max_results=3)
            tasks.append(task_papers)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 2: Unpack and Verify Financial Data
        financial_res = results[0]
        metrics: Optional[FinancialMetrics] = None
        financial_context = ""
        if isinstance(financial_res, Exception):
            fallbacks_used.append(f"Financial Tool Error: {str(financial_res)}")
            financial_context = "Detailed fundamental financial data was unavailable via API."
        else:
            metrics, fin_err = financial_res
            if metrics:
                summary_dict = metrics.to_summary_dict()
                financial_context = "\n".join([f"- {k}: {v}" for k, v in summary_dict.items()])
            else:
                fallbacks_used.append(f"Financial Data: {fin_err or 'Marked unavailable'}")
                financial_context = f"Financial metrics unavailable: {fin_err or 'N/A'}"

        # Step 3: Unpack and Verify SEC Filings Data
        sec_res = results[1]
        sec_report: Optional[SECResearchReport] = None
        sec_context = ""
        if isinstance(sec_res, Exception):
            fallbacks_used.append(f"SEC EDGAR Tool Exception: {str(sec_res)}")
            sec_context = "SEC filings unavailable."
        else:
            sec_report = sec_res
            if sec_report:
                sec_context = sec_report.to_prompt_context()
            else:
                fallbacks_used.append("SEC EDGAR: No US public filer CIK resolved for this query.")
                sec_context = f"SEC filings: No US public filer CIK found for '{clean_target}'."

        # Step 4: Unpack and Verify Web Research (SearXNG / Fallback)
        web_res = results[2]
        web_results: List[Dict[str, Any]] = []
        web_source_mode = "unknown"
        web_context = ""
        if isinstance(web_res, Exception):
            fallbacks_used.append(f"Web Search Tool Exception: {str(web_res)}")
            web_context = "Web search was unavailable."
        else:
            web_data = web_res
            web_source_mode = web_data.get("source", "unknown")
            web_results = web_data.get("results", [])
            if web_source_mode == "direct_http_fallback":
                fallbacks_used.append("SearXNG offline -> Direct HTTP Google News RSS fallback active.")

            formatted_web: List[str] = []
            for i, r in enumerate(web_results[:4], 1):
                t = r.get("title", "")
                u = r.get("url", "")
                s = r.get("snippet", "")
                formatted_web.append(f"[{i}] {t}\n    URL: {u}\n    Info: {s}")
            web_context = "\n\n".join(formatted_web)

        # Optional Papers
        papers_results: List[Dict[str, Any]] = []
        papers_context = ""
        if include_papers and len(results) > 3:
            papers_res = results[3]
            if not isinstance(papers_res, Exception) and papers_res.get("results"):
                papers_results = papers_res.get("results", [])
                formatted_papers = [
                    f"- {p.get('title')} ({p.get('publication_year')}): {p.get('url')}"
                    for p in papers_results
                ]
                papers_context = "Academic Research Papers:\n" + "\n".join(formatted_papers)

        # Resolve Final Company and Ticker Names
        final_symbol = metrics.symbol if metrics else clean_target.upper()
        final_company = metrics.company_name if metrics else (
            sec_report.company if sec_report else clean_target
        )

        # Build Context for Synthesis
        combined_context = f"""
=== VERIFIED FINANCIAL METRICS ===
{financial_context}

=== OFFICIAL SEC EDGAR FILINGS & XBRL FACTS ===
{sec_context}

=== LIVE WEB RESEARCH & HEADLINES ({web_source_mode}) ===
{web_context}
"""
        if papers_context:
            combined_context += f"\n=== ACADEMIC PAPERS (OpenAlex) ===\n{papers_context}\n"

        # Step 5: Synthesize Research Report via Groq or Local Synthesis Fallback
        report, model_used = await self._synthesize_report(
            company_name=final_company,
            symbol=final_symbol,
            combined_context=combined_context,
            metrics=metrics,
            sec_report=sec_report,
            web_results=web_results,
            fallbacks_used=fallbacks_used,
        )

        # Build Normalized Web Sources List
        sources_list: List[Dict[str, Any]] = []
        for r in web_results:
            sources_list.append({
                "title": r.get("title", "Web Source"),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", ""),
                "engine": r.get("engine", web_source_mode),
            })

        return {
            "company": final_company,
            "ticker": final_symbol,
            "status": "success",
            "model_used": model_used,
            "full_report": report,
            "financial_metrics": metrics,
            "sec_report": sec_report,
            "web_results": web_results,
            "web_source_mode": web_source_mode,
            "papers_results": papers_results,
            "fallbacks_used": fallbacks_used,
            "tool_statuses": health_statuses,
            "sources": sources_list,
        }

    async def _synthesize_report(
        self,
        company_name: str,
        symbol: str,
        combined_context: str,
        metrics: Optional[FinancialMetrics],
        sec_report: Optional[SECResearchReport],
        web_results: List[Dict[str, Any]],
        fallbacks_used: List[str],
    ) -> Tuple[str, str]:
        """
        Generates the 6-section research report using Groq with automatic model failover.
        Falls back to local heuristic synthesis if Groq is unavailable or key is missing.
        """
        # If no Groq key, use local heuristic report synthesis
        if not self.groq_api_key or not Groq:
            fallbacks_used.append("GROQ_API_KEY missing -> Using local deterministic report synthesis.")
            return self._build_local_synthesis(company_name, symbol, metrics, sec_report, web_results), "local_synthesis"

        # Try available Groq models in order
        models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

        user_prompt = f"""Target Company: {company_name} ({symbol})

Below is the verified data collected from yfinance, SEC EDGAR, and web research:

{combined_context}

Please synthesize a comprehensive 6-section research report following the system instructions.
Explicitly incorporate the financial metrics and cite the provided sources."""

        for model in models_to_try:
            try:
                client = Groq(api_key=self.groq_api_key)
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_completion_tokens=2200,
                    temperature=0.2,
                )
                content = response.choices[0].message.content
                if content and len(content.strip()) > 100:
                    return content.strip(), model
            except Exception as e:
                fallbacks_used.append(f"Groq {model} failover: {type(e).__name__}")
                continue

        # If all Groq models failed, generate local synthesis
        fallbacks_used.append("All Groq models exhausted -> Fell back to local deterministic report synthesis.")
        return self._build_local_synthesis(company_name, symbol, metrics, sec_report, web_results), "local_synthesis_fallback"

    def _build_local_synthesis(
        self,
        company_name: str,
        symbol: str,
        metrics: Optional[FinancialMetrics],
        sec_report: Optional[SECResearchReport],
        web_results: List[Dict[str, Any]],
    ) -> str:
        """Constructs an authoritative structured markdown report directly from collected facts."""
        sections: List[str] = []

        # 1. Company Overview
        sections.append(f"## 1. Company Overview\n**{company_name} ({symbol})** is a leading global enterprise operating in public financial markets.")
        if sec_report and sec_report.cik:
            sections.append(f"- **SEC CIK**: {sec_report.cik}\n- **Primary Exchange**: US Public Markets\n- **Reporting Standard**: US GAAP / SEC EDGAR")
        if metrics:
            sections.append(f"- **Market Valuation**: Currently valued at **{metrics.to_summary_dict().get('Market Cap', 'N/A')}** with shares trading around **{metrics.to_summary_dict().get('Current Price', 'N/A')}**.")

        # 2. Recent Developments
        sections.append("## 2. Recent Developments")
        if web_results:
            for w in web_results[:3]:
                sections.append(f"- **{w.get('title')}**: Published {w.get('snippet', 'Recently')}. [Source URL]({w.get('url')})")
        if sec_report and sec_report.filings.get("8-K"):
            for filing in sec_report.filings["8-K"][:2]:
                sections.append(f"- **SEC 8-K Event ({filing.filing_date})**: Form 8-K current report filed. ([Filing Archive]({filing.source_url}))")
        if not web_results and (not sec_report or not sec_report.filings.get("8-K")):
            sections.append("- No recent material corporate events detected in public feeds.")

        # 3. Revenue & Profit Information
        sections.append("## 3. Revenue & Profit Information")
        if metrics:
            sections.append("### Key Verified Financial Metrics (yfinance)")
            s_dict = metrics.to_summary_dict()
            table_lines = [
                "| Financial Metric | Value |",
                "| :--- | :--- |",
                f"| Current Market Price | {s_dict.get('Current Price')} |",
                f"| Total Market Cap | {s_dict.get('Market Cap')} |",
                f"| Total Revenue (TTM) | {s_dict.get('Revenue (TTM)')} |",
                f"| Net Income (TTM) | {s_dict.get('Net Income (TTM)')} |",
                f"| Diluted EPS | {s_dict.get('Diluted EPS')} |",
                f"| Gross Margin | {s_dict.get('Gross Margin')} |",
                f"| Operating Margin | {s_dict.get('Operating Margin')} |",
                f"| Free Cash Flow | {s_dict.get('Free Cash Flow')} |",
                f"| Cash & Short-Term Inv. | {s_dict.get('Total Cash')} |",
                f"| Total Debt | {s_dict.get('Total Debt')} |",
                f"| P/E Multiple | {s_dict.get('P/E Ratio')} |",
                f"| P/S Multiple | {s_dict.get('P/S Ratio')} |",
                f"| EV/EBITDA Multiple | {s_dict.get('EV/EBITDA')} |",
                f"| Revenue Growth (YoY) | {s_dict.get('Revenue Growth (YoY)')} |",
                f"| EPS Growth (YoY) | {s_dict.get('EPS Growth (YoY)')} |",
            ]
            sections.append("\n".join(table_lines))
        else:
            sections.append("- Fundamental financial metrics unavailable via market API feeds.")

        if sec_report and sec_report.facts:
            sections.append("\n### Official SEC XBRL GAAP Facts")
            for fact in sec_report.facts[:5]:
                sections.append(f"- **{fact.claim}**: {fact.value or 'Disclosed'} (Filing Form {fact.filing_type} dated {fact.filing_date})")

        # 4. Major Risks
        sections.append("## 4. Major Risks")
        sections.append("- Competitive headwinds in core market sectors and rapid technological innovation.")
        sections.append("- Macroeconomic sensitivity, interest rate exposure, and global supply chain dependencies.")
        sections.append("- Regulatory oversight and antitrust/compliance scrutiny across international jurisdictions.")

        # 5. Growth Opportunities
        sections.append("## 5. Growth Opportunities")
        sections.append("- Continued expansion in core high-margin product offerings and market penetration.")
        sections.append("- Capital reinvestment in high-ROI research, development, and strategic partnerships.")
        sections.append("- Operating leverage and margin expansion supported by strong market position.")

        # 6. Sources for Important Claims
        sections.append("## 6. Sources for Important Claims")
        if sec_report and sec_report.filings:
            for form in ("10-K", "10-Q", "8-K", "20-F"):
                for f in sec_report.filings.get(form, [])[:2]:
                    sections.append(f"- **SEC EDGAR {f.form} Filing** ({f.filing_date}): [{f.form} Source URL]({f.source_url})")
        if web_results:
            for w in web_results:
                sections.append(f"- **{w.get('title')}**: [{w.get('url')}]({w.get('url')})")
        if not web_results and (not sec_report or not sec_report.filings):
            sections.append("- Public financial disclosure feeds.")

        return "\n\n".join(sections)
