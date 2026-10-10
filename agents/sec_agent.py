"""
SEC Research Agent
Autonomous specialist agent for SEC EDGAR disclosures.
Retrieves and parses 10-K, 10-Q, 8-K, 20-F, Form 4, and XBRL company facts.
Returns strongly-typed Pydantic objects with exact source URLs, dates, and accessions.
"""

import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from tools.sec.sec_client import SECClient
from tools.sec.sec_parser import (
    SECParser,
    SECExtractedFact,
    SECFilingMeta,
    SECInsiderTransaction,
)

logger = logging.getLogger(__name__)


class SECResearchReport(BaseModel):
    """Complete structured research report generated from official SEC EDGAR filings."""
    company: str = Field(description="Official company name")
    ticker: str = Field(description="Official stock ticker symbol")
    cik: str = Field(description="10-digit zero-padded SEC Central Index Key")
    facts: List[SECExtractedFact] = Field(default_factory=list, description="Extracted facts with citations")
    filings: Dict[str, List[SECFilingMeta]] = Field(default_factory=dict, description="Recent filings categorized by form")
    insider_transactions: List[SECInsiderTransaction] = Field(default_factory=list, description="Recent Form 4 insider transactions")
    financial_metrics: Dict[str, Any] = Field(default_factory=dict, description="Summary of extracted and derived financial metrics")

    def to_json(self, indent: int = 2) -> str:
        """Serializes the report to structured JSON."""
        return self.model_dump_json(indent=indent)

    def format_console_summary(self) -> str:
        """Formats the key SEC findings into clean, readable terminal tables."""
        lines = []
        width = 68
        border = "+" + "-" * (width - 2) + "+"

        # Header
        lines.append(border)
        lines.append(f"| {f'SEC EDGAR RESEARCH: {self.company} ({self.ticker}) | CIK: {self.cik}'.center(width - 4)} |")
        lines.append(border)

        # 1. Recent Key Filings
        lines.append(f"| {'RECENT OFFICIAL FILINGS'.center(width - 4)} |")
        lines.append(border)
        lines.append(f"| {'Form'.ljust(8)} | {'Filing Date'.ljust(12)} | {'Accession Number'.ljust(22)} | {'Doc'.ljust(15)} |")
        lines.append("+" + "-" * 10 + "+" + "-" * 14 + "+" + "-" * 24 + "+" + "-" * 16 + "+")

        filing_count = 0
        for form in ("10-K", "10-Q", "8-K", "20-F"):
            for filing in self.filings.get(form, [])[:2]:
                doc_name = filing.primary_doc.split("/")[-1][:15]
                lines.append(f"| {filing.form.ljust(8)} | {filing.filing_date.ljust(12)} | {filing.accession_number[:22].ljust(22)} | {doc_name.ljust(15)} |")
                filing_count += 1

        if filing_count == 0:
            lines.append(f"| {'No recent 10-K/10-Q/8-K filings found.'.center(width - 4)} |")
        lines.append(border)

        # 2. Key Extracted Facts & Financials
        if self.facts:
            lines.append(f"| {'EXTRACTED FACTS & SEC GAAPS'.center(width - 4)} |")
            lines.append(border)
            lines.append(f"| {'Metric / Claim'.ljust(34)} | {'Value'.ljust(14)} | {'Source Form'.ljust(12)} |")
            lines.append("+" + "-" * 36 + "+" + "-" * 16 + "+" + "-" * 13 + "+")
            for fact in self.facts:
                if "Item 1A" in fact.claim or "Management Commentary" in fact.claim or "Material Event" in fact.claim:
                    continue
                claim_str = fact.claim[:34].ljust(34)
                val_str = (fact.value or "Reported")[:14].ljust(14)
                form_str = f"{fact.filing_type} ({fact.filing_date})"[ :12].ljust(12)
                lines.append(f"| {claim_str} | {val_str} | {form_str} |")
            lines.append(border)

        # 3. Recent Insider Trades
        if self.insider_transactions:
            lines.append(f"| {'RECENT FORM 4 INSIDER TRANSACTIONS'.center(width - 4)} |")
            lines.append(border)
            lines.append(f"| {'Reporting Owner'.ljust(22)} | {'Type'.ljust(14)} | {'Shares'.ljust(10)} | {'Date'.ljust(12)} |")
            lines.append("+" + "-" * 24 + "+" + "-" * 16 + "+" + "-" * 12 + "+" + "-" * 13 + "+")
            for trade in self.insider_transactions[:4]:
                owner = trade.reporting_owner[:22].ljust(22)
                ttype = trade.transaction_type[:14].ljust(14)
                shares_str = f"{trade.shares:,.0f}" if trade.shares else "N/A"
                shares_str = shares_str[:10].ljust(10)
                date_str = trade.transaction_date[:12].ljust(12)
                lines.append(f"| {owner} | {ttype} | {shares_str} | {date_str} |")
            lines.append(border)

        return "\n".join(lines)

    def to_prompt_context(self) -> str:
        """Converts extracted facts into grounded context for the final LLM report."""
        sections = [
            f"OFFICIAL SEC EDGAR FILINGS CONTEXT FOR {self.company} (Ticker: {self.ticker}, CIK: {self.cik}):"
        ]

        if self.facts:
            sections.append("\nVerified SEC Facts & Disclosures:")
            for fact in self.facts:
                sections.append(
                    f"- {fact.claim}: {fact.value or 'Disclosed'}\n"
                    f"  Filing: Form {fact.filing_type} (Filed: {fact.filing_date}, Accn: {fact.accession_number})\n"
                    f"  Source URL: {fact.source_url}\n"
                    f"  Snippet: {fact.source_snippet}"
                )

        if self.insider_transactions:
            sections.append("\nRecent Form 4 Insider Transactions:")
            for trade in self.insider_transactions[:4]:
                val_txt = f" (Est. Total: ${trade.total_value:,.2f})" if trade.total_value else ""
                sh_txt = f"{trade.shares:,.0f}" if trade.shares else "N/A"
                sections.append(
                    f"- {trade.reporting_owner} ({trade.officer_title or 'Director/Officer'}): "
                    f"{trade.transaction_type} {sh_txt} shares on {trade.transaction_date}{val_txt}\n"
                    f"  Filing Date: {trade.filing_date} | Source: {trade.source_url}"
                )

        if self.filings:
            sections.append("\nDirect SEC Filing Links:")
            for form in ("10-K", "10-Q", "8-K", "20-F"):
                for filing in self.filings.get(form, [])[:2]:
                    sections.append(f"- Form {filing.form} (Filed {filing.filing_date}): {filing.source_url}")

        return "\n".join(sections)


class SECAgent:
    """Agent that performs read-only research against SEC EDGAR."""

    def __init__(self, client: Optional[SECClient] = None):
        self.client = client or SECClient()
        self.parser = SECParser()

    def run(self, ticker_or_company: str) -> Optional[SECResearchReport]:
        """
        Executes end-to-end research against SEC EDGAR.
        Returns a structured SECResearchReport or None if company is not a registered US public filer.
        """
        # Step 1: Resolve CIK
        cik_info = self.client.get_cik(ticker_or_company)
        if not cik_info:
            logger.info(f"No SEC CIK found for query '{ticker_or_company}'.")
            return None

        cik, official_ticker, company_name = cik_info

        # Step 2: Fetch recent submissions
        submissions = self.client.get_submissions(cik)
        if not submissions:
            logger.warning(f"Could not retrieve submissions for CIK {cik}.")
            return None

        filings_by_form = self.parser.parse_recent_filings(submissions, cik, self.client)

        # Step 3: Fetch XBRL facts
        facts_json = self.client.get_company_facts(cik)
        facts_list: List[SECExtractedFact] = []
        metrics_summary: Dict[str, Any] = {}

        if facts_json:
            facts_list, metrics_summary = self.parser.parse_xbrl_facts(
                facts_json, cik, official_ticker, company_name, self.client
            )

        # Step 4: Parse recent Form 4 insider transactions
        insider_trades: List[SECInsiderTransaction] = []
        for form4_meta in filings_by_form.get("4", [])[:3]:
            # Fetch Form 4 XML or document
            doc_xml = self.client.get_filing_document(
                cik, form4_meta.accession_number, form4_meta.primary_doc
            )
            if doc_xml:
                trades = self.parser.parse_form4_xml(
                    doc_xml,
                    cik,
                    form4_meta.accession_number,
                    form4_meta.filing_date,
                    official_ticker,
                    company_name,
                    form4_meta.source_url,
                )
                insider_trades.extend(trades)

        # Step 5: Parse recent Form 8-K major events
        for k8_meta in filings_by_form.get("8-K", [])[:2]:
            doc_html = self.client.get_filing_document(
                cik, k8_meta.accession_number, k8_meta.primary_doc
            )
            if doc_html:
                events = self.parser.parse_8k_events(
                    doc_html, k8_meta, official_ticker, company_name
                )
                facts_list.extend(events)

        # Step 6: Extract Risk Factors and MD&A from latest 10-Q or 10-K
        primary_filing = None
        if filings_by_form.get("10-Q"):
            primary_filing = filings_by_form["10-Q"][0]
        elif filings_by_form.get("10-K"):
            primary_filing = filings_by_form["10-K"][0]

        if primary_filing:
            doc_content = self.client.get_filing_document(
                cik, primary_filing.accession_number, primary_filing.primary_doc
            )
            if doc_content:
                risk_fact = self.parser.parse_risk_factors(
                    doc_content, primary_filing, official_ticker, company_name
                )
                if risk_fact:
                    facts_list.append(risk_fact)

                mda_fact = self.parser.parse_management_commentary(
                    doc_content, primary_filing, official_ticker, company_name
                )
                if mda_fact:
                    facts_list.append(mda_fact)

        return SECResearchReport(
            company=company_name,
            ticker=official_ticker,
            cik=cik,
            facts=facts_list,
            filings=filings_by_form,
            insider_transactions=insider_trades,
            financial_metrics=metrics_summary,
        )
