"""
Stock Research Agent
An advanced, single-agent financial analyst that combines:
1. Fundamental Financial Data API & Python Calculations (Price, Multiples, Margins, Cash Flow, Growth).
2. Groq's live web-search and tool-use capabilities (Built-in Browser Search & Function Calling).
"""

import os
import sys
from pathlib import Path

import json
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple

try:
    import requests
    import dotenv
    import groq
except ImportError:
    from env_bootstrap import bootstrap_environment
    bootstrap_environment(["requests", "dotenv", "groq", "pydantic", "yfinance"])

import requests
import asyncio
from dotenv import load_dotenv
from groq import Groq, GroqError

from financial_data import fetch_financial_data, FinancialMetrics
from agents.sec_agent import SECAgent, SECResearchReport
from services.research_service import ResearchService

# Ensure UTF-8 output on Windows consoles to prevent encoding errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load this project's settings regardless of the caller's working directory.
load_dotenv(Path(__file__).resolve().parent / ".env")

SYSTEM_PROMPT = """You are an elite equity research analyst and business intelligence agent.
Your objective is to produce an authoritative, objective, and up-to-date research report on the requested company or stock.

Ground your report in two sources of truth:
1. The verified fundamental financial metrics provided in the prompt (exact numbers, valuation multiples, and margins).
2. Live web search results to retrieve recent developments, strategic events, risks, and forward guidance.

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


def perform_live_web_search(query: str, max_results: int = 3) -> str:
    """
    Fetches real-time web news and articles for a query using requests.
    Returns concise structured results (title, date, publisher, URL) to preserve token budget.
    """
    try:
        encoded_query = urllib.parse.quote_plus(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(rss_url, headers=headers, timeout=8)
        response.raise_for_status()

        root = ET.fromstring(response.text)
        items = root.findall(".//item")

        if not items:
            return f"No news articles found for: '{query}'."

        formatted_results = []
        for i, item in enumerate(items[:max_results], 1):
            title = (item.find("title").text if item.find("title") is not None else "No Title").strip()
            link = (item.find("link").text if item.find("link") is not None else "").strip()
            pub_date = (item.find("pubDate").text if item.find("pubDate") is not None else "Recent").strip()
            # Trim title to keep token count compact
            if len(title) > 120:
                title = title[:117] + "..."
            formatted_results.append(
                f"[{i}] {title}\n    Published: {pub_date}\n    URL: {link}"
            )

        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error executing web search for '{query}': {str(e)}"


# Tool definitions for Groq function-calling tool-use
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Searches the live web for recent financial news, earnings reports, business updates, risks, and market developments for a given company or stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Specific search query (e.g., 'NVIDIA latest earnings revenue profit risks 2026')",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_metrics",
            "description": "Fetches verified fundamental financial metrics (price, P/E, P/S, EV/EBITDA, margins, debt, revenue, growth) for any stock symbol or company name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_or_ticker": {
                        "type": "string",
                        "description": "Company name or ticker symbol (e.g. 'AAPL', 'Tesla', 'MSFT')",
                    }
                },
                "required": ["company_or_ticker"],
            },
        },
    },
]


def research_with_builtin_browser(
    client: Groq,
    company_name: str,
    financial_context: str,
    models_to_try: List[str],
) -> Optional[str]:
    """
    Attempts to use Groq's built-in 'browser_search' tool on supported models.
    Supports automatic failover between models (e.g. from 120b to 20b if rate limited).
    """
    for model in models_to_try:
        try:
            print(f"[*] Querying Groq built-in browser_search (Model: {model})...")
            user_message = (
                f"Perform comprehensive equity research on '{company_name}'.\n\n"
                f"VERIFIED FINANCIAL DATA:\n{financial_context}\n\n"
                f"Instructions:\n"
                f"1. Search the web for current 2026 news, recent business developments, competitive risks, and future outlook.\n"
                f"2. Integrate the verified financial figures into Section 3.\n"
                f"3. Strictly format the final answer into the 6 required numbered sections with explicit sources."
            )

            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                tools=[{"type": "browser_search"}],
                tool_choice="auto",
            )

            content = completion.choices[0].message.content
            if content and len(content.strip()) > 50:
                return content

        except Exception as exc:
            err_str = str(exc)
            if "rate_limit" in err_str.lower() or "429" in err_str:
                print(f"[-] Rate limit encountered on {model}. Attempting fallback...")
            else:
                print(f"[-] Notice on model {model}: {err_str}")

    return None


def research_with_tool_calling(
    client: Groq,
    company_name: str,
    financial_context: str,
    model: str = "qwen/qwen3.8-27b",
) -> str:
    """
    Executes an autonomous research loop using Groq tool-use (function calling) with live web search.
    Protected against token-budget limits and rate limits.
    """
    print(f"[*] Running Groq tool-use research loop (Model: {model})...")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Perform comprehensive equity research on: '{company_name}'.\n\n"
                f"VERIFIED FINANCIAL DATA:\n{financial_context}\n\n"
                f"Use the 'web_search' tool to check 1 or 2 recent updates if needed. "
                f"Then generate the full structured 6-section research report."
            ),
        },
    ]

    max_turns = 3
    for turn in range(max_turns):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.2,
            )
        except Exception as e:
            print(f"[!] Tool loop API notice on {model}: {e}")
            break

        response_message = response.choices[0].message

        if response_message.tool_calls:
            messages.append(response_message)
            # Limit parallel calls to prevent hitting 7,000 ITPM limit
            active_calls = response_message.tool_calls[:2]
            for tool_call in active_calls:
                fn_name = tool_call.function.name
                fn_args_raw = tool_call.function.arguments

                try:
                    args = json.loads(fn_args_raw)
                except Exception:
                    args = {}

                if fn_name == "web_search":
                    query = args.get("query", company_name)
                    print(f"    [Tool Call] web_search(query='{query}')")
                    tool_output = perform_live_web_search(query, max_results=2)
                elif fn_name == "get_financial_metrics":
                    target = args.get("company_or_ticker", company_name)
                    print(f"    [Tool Call] get_financial_metrics(target='{target}')")
                    m, _ = fetch_financial_data(target)
                    tool_output = json.dumps(m.to_summary_dict() if m else {"error": "Unavailable"})
                else:
                    tool_output = f"Unknown tool: {fn_name}"

                # Trim output if too long
                if len(tool_output) > 400:
                    tool_output = tool_output[:397] + "..."

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": fn_name,
                        "content": tool_output,
                    }
                )
        else:
            return response_message.content or "No report content generated."

    # Final synthesis if loop completed tool calls
    try:
        messages.append(
            {
                "role": "user",
                "content": "Synthesize the verified financial data and findings into the final 6-section report now.",
            }
        )
        final_response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        return final_response.choices[0].message.content or "Report generated."
    except Exception as synth_err:
        return (
            f"# Research Summary: {company_name}\n\n"
            f"### Verified Financial Metrics:\n{financial_context}\n\n"
            f"*(Note: Groq LLM token capacity was temporarily constrained: {synth_err}. Financial metrics were verified and printed above.)*"
        )


def run_stock_research(company_name: str) -> None:
    """
    Main research pipeline backed by the free, local-first architecture.
    Orchestrates yfinance, SEC EDGAR, SearXNG MCP / fallback, and SQLite persistence.
    """
    service = ResearchService()

    print("\n" + "=" * 68)
    print(f"  STOCK RESEARCH AGENT: Initiating Analysis for '{company_name}'")
    print("=" * 68)

    # -------------------------------------------------------------
    # Step 1: Health Checks & MCP Connection Status
    # -------------------------------------------------------------
    health = service.get_health_status()
    print("\n[*] Tool & MCP Connection Status:")
    for tool_name, info in health.items():
        st = info.get("status", "unknown").upper()
        mode = info.get("active_mode", "")
        msg = info.get("message", "")
        print(f"    - {tool_name.ljust(16)}: [{st}] (Mode: {mode}) -> {msg}")

    print(f"\n[*] Executing concurrent research across yfinance, SEC EDGAR, and web...")
    result = asyncio.run(service.execute_research(company_name))

    # -------------------------------------------------------------
    # Step 2: Financial Results (yfinance)
    # -------------------------------------------------------------
    metrics = result.get("financial_metrics")
    print("\n" + "-" * 68)
    print("  FINANCIAL RESULTS (yfinance & Python calculations)")
    print("-" * 68)
    if metrics:
        print(metrics.format_table())
    else:
        print("  [!] Financial metrics unavailable.")

    # -------------------------------------------------------------
    # Step 3: SEC EDGAR Regulatory Results
    # -------------------------------------------------------------
    sec_report = result.get("sec_report")
    print("\n" + "-" * 68)
    print("  SEC EDGAR REGULATORY RESULTS")
    print("-" * 68)
    if sec_report:
        print(sec_report.format_console_summary())
    else:
        print(f"  [!] SEC EDGAR filings unavailable for '{company_name}'.")

    # -------------------------------------------------------------
    # Step 4: Web Results & Engine Status
    # -------------------------------------------------------------
    web_results = result.get("web_results", [])
    web_mode = result.get("web_source_mode", "unknown")
    print("\n" + "-" * 68)
    print(f"  WEB RESEARCH RESULTS (Active Engine: {web_mode})")
    print("-" * 68)
    if web_results:
        for i, w in enumerate(web_results, 1):
            print(f"  [{i}] {w.get('title')}")
            print(f"      URL: {w.get('url')}")
            if w.get('snippet'):
                print(f"      Snippet: {w.get('snippet')}")
    else:
        print("  [!] No web search results retrieved.")

    # -------------------------------------------------------------
    # Step 5: Failures & Fallbacks Notice
    # -------------------------------------------------------------
    fallbacks = result.get("fallbacks_used", [])
    print("\n" + "-" * 68)
    print("  FAILURES & FALLBACKS STATUS")
    print("-" * 68)
    if fallbacks:
        for fb in fallbacks:
            print(f"  [i] Notice/Fallback: {fb}")
    else:
        print("  [✓] All tools executed with zero fallbacks required.")

    # -------------------------------------------------------------
    # Step 6: Final Synthesized Equity Research Report
    # -------------------------------------------------------------
    header_name = result.get("company", company_name)
    header_symbol = f" ({result.get('ticker')})" if result.get('ticker') else ""
    model_used = result.get("model_used", "local_synthesis")

    print("\n" + "=" * 68)
    print(f"  EQUITY RESEARCH REPORT: {header_name.upper()}{header_symbol} [Model: {model_used}]")
    print("=" * 68 + "\n")
    print(result.get("full_report", "No report generated."))
    print("\n" + "=" * 68)
    print(f"  [✓] Session successfully persisted to SQLite (Session ID: {result.get('session_id')})")
    print("=" * 68 + "\n")


def main():
    # Support launching GUI via flags
    if "--gui" in sys.argv or "--windows" in sys.argv:
        from gui import launch_gui
        print("[*] Launching Windows Native GUI...")
        launch_gui()
        return

    if "--ui" in sys.argv:
        from ui.app import launch_ui
        print("[*] Launching Flet Desktop UI...")
        launch_ui()
        return

    print("=" * 68)
    print("   BUSSIWZZ - AI STOCK RESEARCH AGENT                               ")
    print("   (Zero Paid Search | yfinance | SEC EDGAR | SQLite Storage)       ")
    print("=" * 68)

    # Allow passing company name directly as a command line argument (excluding flags)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        target = " ".join(args).strip()
        run_stock_research(target)
        return

    # Interactive prompt loop
    while True:
        try:
            print("\nEnter a stock symbol or company name (or 'exit' to quit):")
            company_input = input("> ").strip()
            if not company_input:
                continue
            if company_input.lower() in ("exit", "quit", "q"):
                print("Exiting Stock Research Agent. Goodbye!")
                break

            run_stock_research(company_input)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Goodbye!")
            break


if __name__ == "__main__":
    main()
