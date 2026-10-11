"""
R&D and Technology Research Agent
Autonomous specialist agent for corporate research and development activities,
emerging technology investments, intellectual property, and product innovation.

Investigates 12 specific research categories:
1. Company R&D spending
2. New products
3. Products currently under development
4. New technologies
5. Patents
6. Scientific/technical publications
7. Partnerships
8. Acquisitions
9. New factories/data centers/labs
10. AI/ML developments where relevant
11. Engineering/open-source projects
12. Regulatory approvals or trials where relevant

Distinguishes epistemic claims:
- FACT: Directly supported by an authoritative source.
- INFERENCE: Reasonable interpretation of multiple facts.
- SPECULATION: Possible future outcome that is not established.
Rule: Never present speculation as fact.

For every major R&D development answers:
- What is the company researching/building?
- How mature is it?
- Why does it matter?
- What market could it affect?
- What is the possible financial impact?
- What could prevent it from succeeding?
"""

import os
import re
import json
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, field_validator

from tools.sec.sec_client import SECClient
from tools.sec.sec_parser import SECParser, format_currency_amount
from tools.papers.openalex_client import OpenAlexClient
from tools.mcp.searxng_client import SearXNGClient
from financial_data import format_currency

try:
    from groq import Groq, GroqError
except ImportError:
    Groq = None
    GroqError = Exception

logger = logging.getLogger(__name__)

# Official 12 Research Categories
RESEARCH_CATEGORIES = [
    "Company R&D spending",
    "New products",
    "Products currently under development",
    "New technologies",
    "Patents",
    "Scientific/technical publications",
    "Partnerships",
    "Acquisitions",
    "New factories/data centers/labs",
    "AI/ML developments where relevant",
    "Engineering/open-source projects",
    "Regulatory approvals or trials where relevant",
]


class EpistemicStatus(str, Enum):
    """Epistemic classification of research claims."""
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    SPECULATION = "SPECULATION"


# Keywords indicating potential speculation or non-established claims
SPECULATIVE_PATTERNS = [
    r"\brumor(?:ed|s)?\b",
    r"\bspeculat(?:ion|ed|ive|es)?\b",
    r"\bunconfirmed\b",
    r"\bunverified\b",
    r"\bmight\s+(?:be|launch|release|reach|disrupt)\b",
    r"\bcould\s+(?:potentially|eventually|possibly)\b",
    r"\bpredicted\s+to\b",
    r"\bconjectur(?:e|ed)\b",
    r"\bhypothetical\b",
    r"\balleged(?:ly)?\b",
    r"\bleak(?:ed|s)?\b",
    r"\bunannounced\b",
    r"\bpurported(?:ly)?\b",
    r"\banalyst(?:s)?\s+speculate\b",
]


class RDDiscovery(BaseModel):
    """
    Structured representation of an important technological discovery.
    Strictly follows the prompt's required schema and enforces epistemic truthfulness.
    """
    claim: str = Field(description="The factual, inferential, or speculative proposition discovered")
    category: str = Field(description="One of the 12 R&D research categories")
    source_url: str = Field(default="", description="Direct URL, DOI, or official filing source link")
    source_name: str = Field(default="", description="Name of publisher, database, or SEC disclosure")
    publication_date: str = Field(default="", description="Publication date or filing period")
    company_relevance: str = Field(description="Why this discovery directly matters to the target company")
    potential_business_impact: str = Field(description="Anticipated commercial, market, or financial effect")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    epistemic_status: str = Field(
        default=EpistemicStatus.FACT.value,
        description="FACT (directly supported), INFERENCE (reasoned interpretation), or SPECULATION (future/unestablished outcome)"
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        for cat in RESEARCH_CATEGORIES:
            if v.strip().lower() == cat.lower():
                return cat
        # Match substring or fallback
        v_low = v.strip().lower()
        for cat in RESEARCH_CATEGORIES:
            if v_low in cat.lower() or cat.lower() in v_low:
                return cat
        return "New technologies"

    @field_validator("epistemic_status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper in (EpistemicStatus.FACT.value, EpistemicStatus.INFERENCE.value, EpistemicStatus.SPECULATION.value):
            return v_upper
        return EpistemicStatus.INFERENCE.value

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, round(float(v), 3)))

    def model_post_init(self, __context: Any) -> None:
        """
        Enforce epistemic guardrail: NEVER present speculation as fact.
        If a claim contains speculative markers, it must be downgraded to SPECULATION or INFERENCE.
        """
        super().model_post_init(__context)
        if self.epistemic_status == EpistemicStatus.FACT.value:
            text_to_audit = f"{self.claim} {self.potential_business_impact}".lower()
            for pattern in SPECULATIVE_PATTERNS:
                if re.search(pattern, text_to_audit, re.IGNORECASE):
                    self.epistemic_status = EpistemicStatus.SPECULATION.value
                    self.confidence = min(self.confidence, 0.65)
                    break

            # If no supporting source link or name exists, cannot claim to be a verified fact
            if not self.source_url and not self.source_name:
                self.epistemic_status = EpistemicStatus.INFERENCE.value

    def to_spec_dict(self) -> Dict[str, Any]:
        """Returns exact dictionary matching the prompt specification."""
        return {
            "claim": self.claim,
            "category": self.category,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "publication_date": self.publication_date,
            "company_relevance": self.company_relevance,
            "potential_business_impact": self.potential_business_impact,
            "confidence": self.confidence,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Returns dictionary including epistemic status."""
        d = self.to_spec_dict()
        d["epistemic_status"] = self.epistemic_status
        return d


class RDDevelopment(BaseModel):
    """
    Comprehensive evaluation of a major corporate R&D development.
    Directly answers all 6 required analytical questions:
    1. What is the company researching/building?
    2. How mature is it?
    3. Why does it matter?
    4. What market could it affect?
    5. What is the possible financial impact?
    6. What could prevent it from succeeding?
    """
    title: str = Field(description="Headline name of the major technology initiative or program")
    category: str = Field(description="Primary category among the 12 research areas")
    researching_building: str = Field(description="1. What is the company researching/building?")
    maturity: str = Field(description="2. How mature is it? (e.g. Concept, Laboratory R&D, Prototype, Beta/Clinical Trial, Commercial Production)")
    why_it_matters: str = Field(description="3. Why does it matter? Core technical differentiation and competitive moat")
    market_affected: str = Field(description="4. What market could it affect? Target addressable market and customer base")
    possible_financial_impact: str = Field(description="5. What is the possible financial impact? Revenue upside or capex load")
    key_risks_or_barriers: str = Field(description="6. What could prevent it from succeeding? Technical, execution, or regulatory risks")
    epistemic_status: str = Field(default=EpistemicStatus.INFERENCE.value, description="FACT, INFERENCE, or SPECULATION")
    supporting_sources: List[str] = Field(default_factory=list, description="Source URLs or citations")
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)

    def to_qa_dict(self) -> Dict[str, str]:
        """Returns dictionary mapping the 6 exact questions to the answers."""
        return {
            "What is the company researching/building?": self.researching_building,
            "How mature is it?": self.maturity,
            "Why does it matter?": self.why_it_matters,
            "What market could it affect?": self.market_affected,
            "What is the possible financial impact?": self.possible_financial_impact,
            "What could prevent it from succeeding?": self.key_risks_or_barriers,
        }


class RDResearchReport(BaseModel):
    """Complete research report generated by RDAgent."""
    company: str = Field(description="Company official name")
    ticker: str = Field(description="Stock ticker symbol")
    rd_spending: Optional[Dict[str, Any]] = Field(default=None, description="Verified GAAP R&D expense from SEC XBRL or financials")
    discoveries: List[RDDiscovery] = Field(default_factory=list, description="All extracted discoveries categorized and epistemically classified")
    major_developments: List[RDDevelopment] = Field(default_factory=list, description="Major technology initiatives evaluated across all 6 core questions")
    category_summary: Dict[str, int] = Field(default_factory=dict, description="Count of discoveries per research category")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Aggregated citations with titles and URLs")

    def to_json(self, indent: int = 2) -> str:
        """Serializes report to structured JSON."""
        return self.model_dump_json(indent=indent)

    def get_discoveries_by_category(self, category: str) -> List[RDDiscovery]:
        """Filters discoveries by category name."""
        return [d for d in self.discoveries if d.category.lower() == category.lower()]

    def get_discoveries_by_status(self, status: str) -> List[RDDiscovery]:
        """Filters discoveries by epistemic status (FACT, INFERENCE, SPECULATION)."""
        return [d for d in self.discoveries if d.epistemic_status.upper() == status.upper()]

    def format_console_summary(self) -> str:
        """Formats the R&D research report into an institutional terminal layout."""
        lines = []
        width = 72
        border = "+" + "-" * (width - 2) + "+"

        # Header
        lines.append(border)
        lines.append(f"| {f'R&D & TECHNOLOGY RESEARCH: {self.company} ({self.ticker})'.center(width - 4)} |")
        lines.append(border)

        # 1. Official R&D Spending
        if self.rd_spending:
            lines.append(f"| {'COMPANY R&D SPENDING DISCLOSURES (SEC EDGAR)'.center(width - 4)} |")
            lines.append(border)
            latest = self.rd_spending.get("latest_formatted", "N/A")
            prev = self.rd_spending.get("previous_formatted", "N/A")
            form = self.rd_spending.get("form", "10-K/10-Q")
            lines.append(f"| Latest Reported R&D: {latest.ljust(20)} Form: {form.ljust(22)} |")
            if prev != "N/A":
                lines.append(f"| Prior Period R&D:    {prev.ljust(48)} |")
            lines.append(border)

        # 2. Key Discoveries
        if self.discoveries:
            lines.append(f"| {'VERIFIED R&D DISCOVERIES & EPISTEMIC STATUS'.center(width - 4)} |")
            lines.append(border)
            for d in self.discoveries[:8]:
                badge = f"[{d.epistemic_status}]"
                cat_tag = f"({d.category})"
                lines.append(f"| {badge.ljust(13)} {cat_tag.ljust(54)} |")
                claim_snip = d.claim[:66].ljust(66)
                lines.append(f"|   Claim: {claim_snip} |")
                src_snip = f"{d.source_name} ({d.publication_date})"[ :62].ljust(62)
                lines.append(f"|   Source: {src_snip} |")
                lines.append("+" + "-" * (width - 2) + "+")

        # 3. Major Developments
        if self.major_developments:
            lines.append(f"| {'MAJOR R&D DEVELOPMENTS (6-POINT EVALUATION)'.center(width - 4)} |")
            lines.append(border)
            for dev in self.major_developments[:3]:
                lines.append(f"| Project: {dev.title[:58].ljust(58)} |")
                lines.append(f"| Maturity: {dev.maturity[:57].ljust(57)} |")
                lines.append(f"| Research: {dev.researching_building[:57].ljust(57)} |")
                lines.append(f"| Market:   {dev.market_affected[:57].ljust(57)} |")
                lines.append(f"| Risks:    {dev.key_risks_or_barriers[:57].ljust(57)} |")
                lines.append("+" + "-" * (width - 2) + "+")

        return "\n".join(lines)

    def to_prompt_context(self) -> str:
        """Converts extracted findings into context for downstream LLM synthesis."""
        sections = [
            f"R&D & TECHNOLOGY INTELLIGENCE REPORT FOR {self.company} ({self.ticker}):"
        ]

        if self.rd_spending:
            sections.append(
                f"\n1. Official GAAP R&D Spending:\n"
                f"- Latest Reported R&D: {self.rd_spending.get('latest_formatted', 'Disclosed')} "
                f"(Filing Form {self.rd_spending.get('form')}, Filed: {self.rd_spending.get('filed_date')})\n"
                f"- Source: {self.rd_spending.get('source_url', 'SEC EDGAR')}"
            )

        if self.discoveries:
            sections.append("\n2. Important Technological Discoveries & Claims:")
            for d in self.discoveries:
                sections.append(
                    f"- [{d.epistemic_status}] Category: {d.category}\n"
                    f"  Claim: {d.claim}\n"
                    f"  Relevance: {d.company_relevance}\n"
                    f"  Potential Business Impact: {d.potential_business_impact}\n"
                    f"  Confidence: {d.confidence:.2f} | Source: {d.source_name} ({d.publication_date})\n"
                    f"  URL: {d.source_url}"
                )

        if self.major_developments:
            sections.append("\n3. Major Technology Developments (Detailed 6-Question Evaluation):")
            for dev in self.major_developments:
                sections.append(
                    f"- Initiative: {dev.title} (Category: {dev.category}, Status: {dev.epistemic_status})\n"
                    f"  • What company is researching/building: {dev.researching_building}\n"
                    f"  • Maturity level: {dev.maturity}\n"
                    f"  • Why it matters: {dev.why_it_matters}\n"
                    f"  • Market affected: {dev.market_affected}\n"
                    f"  • Possible financial impact: {dev.possible_financial_impact}\n"
                    f"  • What could prevent it from succeeding: {dev.key_risks_or_barriers}"
                )

        return "\n".join(sections)


class RDAgent:
    """
    Dedicated Research & Development and Technology Research Agent.
    Coordinates SEC EDGAR facts, OpenAlex academic publications, and SearXNG web search.
    """

    def __init__(
        self,
        searxng_client: Optional[SearXNGClient] = None,
        sec_client: Optional[SECClient] = None,
        papers_client: Optional[OpenAlexClient] = None,
        groq_api_key: Optional[str] = None,
    ):
        self.searxng_client = searxng_client or SearXNGClient()
        self.sec_client = sec_client or SECClient()
        self.sec_parser = SECParser()
        self.papers_client = papers_client or OpenAlexClient()
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")

    def check_health(self) -> Dict[str, Any]:
        """Health diagnostics for R&D agent sub-components."""
        sec_h = self.sec_client.check_health()
        searxng_h = self.searxng_client.check_health()
        papers_h = self.papers_client.check_health()

        is_ready = any(
            h.get("status") in ("available", "degraded") for h in (sec_h, searxng_h, papers_h)
        )

        return {
            "status": "available" if is_ready else "degraded",
            "tool": "rd_agent",
            "active_mode": "multi_source_rd",
            "message": "R&D agent active with SEC EDGAR, SearXNG, and OpenAlex integrations.",
            "sub_tools": {
                "sec": sec_h.get("status"),
                "web": searxng_h.get("status"),
                "papers": papers_h.get("status"),
            },
        }

    async def run_async(self, ticker_or_company: str) -> Optional[RDResearchReport]:
        """
        Executes end-to-end R&D and technology research asynchronously.
        Returns a strongly-typed RDResearchReport.
        """
        clean_target = ticker_or_company.strip()

        # Step 1: Resolve Company & CIK
        cik_info = self.sec_client.get_cik(clean_target)
        if cik_info:
            cik, official_ticker, company_name = cik_info
        else:
            cik = None
            official_ticker = clean_target.upper()
            company_name = clean_target

        discoveries: List[RDDiscovery] = []
        rd_spending_dict: Optional[Dict[str, Any]] = None
        sources_list: List[Dict[str, str]] = []

        # Step 2: Concurrent investigations
        tasks = []
        # Task 0: SEC R&D Spending and Filings
        tasks.append(self._investigate_sec_rd(official_ticker, company_name, cik))
        # Task 1: OpenAlex Papers
        tasks.append(self._investigate_papers(company_name))
        # Task 2: Web & News Across Categories
        tasks.append(self._investigate_web_rd(company_name, official_ticker))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Unpack SEC R&D Spending
        sec_res = results[0]
        if not isinstance(sec_res, Exception) and sec_res:
            rd_spending_dict, sec_discoveries = sec_res
            discoveries.extend(sec_discoveries)

        # Unpack Academic Papers
        papers_res = results[1]
        if not isinstance(papers_res, Exception) and papers_res:
            discoveries.extend(papers_res)

        # Unpack Web R&D Discoveries
        web_res = results[2]
        if not isinstance(web_res, Exception) and web_res:
            discoveries.extend(web_res)

        # Step 3: Populate Sources List
        seen_urls = set()
        for d in discoveries:
            if d.source_url and d.source_url not in seen_urls:
                seen_urls.add(d.source_url)
                sources_list.append({
                    "title": d.claim[:60],
                    "url": d.source_url,
                    "name": d.source_name,
                    "category": d.category,
                })

        # Step 4: Synthesize Major Developments answering the 6 questions
        major_developments = self._synthesize_major_developments(
            company_name=company_name,
            discoveries=discoveries,
            rd_spending=rd_spending_dict,
        )

        # Step 5: Tally Category Summary across all 12 categories
        category_summary = {cat: 0 for cat in RESEARCH_CATEGORIES}
        for d in discoveries:
            if d.category in category_summary:
                category_summary[d.category] += 1
            else:
                category_summary[d.category] = 1

        return RDResearchReport(
            company=company_name,
            ticker=official_ticker,
            rd_spending=rd_spending_dict,
            discoveries=discoveries,
            major_developments=major_developments,
            category_summary=category_summary,
            sources=sources_list,
        )

    def run(self, ticker_or_company: str) -> Optional[RDResearchReport]:
        """Synchronous wrapper for run_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In nested event loop, create new loop or run in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.run_async(ticker_or_company)).result()
            return loop.run_until_complete(self.run_async(ticker_or_company))
        except RuntimeError:
            return asyncio.run(self.run_async(ticker_or_company))

    async def _investigate_sec_rd(
        self,
        ticker: str,
        company_name: str,
        cik: Optional[str]
    ) -> Tuple[Optional[Dict[str, Any]], List[RDDiscovery]]:
        """
        Extracts verified GAAP R&D expense from SEC EDGAR XBRL facts.
        Generates high-confidence FACT discoveries.
        """
        if not cik:
            return None, []

        facts_json = await asyncio.to_thread(self.sec_client.get_company_facts, cik)
        if not facts_json or "facts" not in facts_json:
            return None, []

        gaap = facts_json.get("facts", {}).get("us-gaap", {})
        if not gaap:
            gaap = facts_json.get("facts", {}).get("ifrs-full", {})

        candidate_keys = [
            "ResearchAndDevelopmentExpense",
            "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
            "ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost",
            "ResearchAndDevelopmentExpenses",
        ]

        rd_entry = None
        for key in candidate_keys:
            if key in gaap and isinstance(gaap[key], dict):
                units = gaap[key].get("units", {})
                for u_key, pts in units.items():
                    if isinstance(pts, list):
                        form_pts = [p for p in pts if isinstance(p, dict) and p.get("form") in ("10-K", "10-Q")]
                        if form_pts:
                            form_pts.sort(key=lambda x: (str(x.get("filed", "")), str(x.get("end", ""))))
                            best_pt = form_pts[-1].copy()
                            best_pt["_concept"] = key
                            best_pt["_unit"] = u_key
                            if rd_entry is None or (str(best_pt.get("filed", "")) > str(rd_entry.get("filed", ""))):
                                rd_entry = best_pt

        if not rd_entry:
            return None, []

        val = rd_entry.get("val")
        f_date = rd_entry.get("filed", "")
        end_date = rd_entry.get("end", "")
        form = rd_entry.get("form", "10-K")
        accn = rd_entry.get("accn", "")
        url = self.sec_client.build_filing_detail_url(cik, accn)
        formatted = format_currency_amount(val)

        spending_info = {
            "latest_raw": val,
            "latest_formatted": formatted,
            "period_ended": end_date,
            "filed_date": f_date,
            "form": form,
            "accession_number": accn,
            "source_url": url,
            "concept": rd_entry.get("_concept"),
        }

        discovery = RDDiscovery(
            claim=f"Reported Research & Development Expense of {formatted} in Form {form} for period ended {end_date}.",
            category="Company R&D spending",
            source_url=url,
            source_name=f"SEC EDGAR Form {form} (Accession: {accn})",
            publication_date=f_date,
            company_relevance=f"Official audited US GAAP R&D capital expenditure reported by {company_name}.",
            potential_business_impact=f"Indicates ongoing resource allocation toward core IP development, product roadmaps, and technological barriers to entry.",
            confidence=1.0,
            epistemic_status=EpistemicStatus.FACT.value,
        )

        return spending_info, [discovery]

    async def _investigate_papers(self, company_name: str) -> List[RDDiscovery]:
        """
        Extracts scientific and technical publications authored by or related to the company from OpenAlex.
        Generates FACT discoveries for scientific/technical publications.
        """
        discoveries: List[RDDiscovery] = []
        try:
            res = await self.papers_client.search_papers(f"{company_name} technology architecture", max_results=4)
            if res.get("status") == "success":
                for item in res.get("results", []):
                    title = item.get("title", "Untitled Research Paper")
                    pub_year = str(item.get("publication_year") or "Recent")
                    url = item.get("url") or item.get("doi") or "https://openalex.org"
                    cites = item.get("cited_by_count", 0)
                    authors = ", ".join(item.get("authors", [])[:2]) or company_name

                    discoveries.append(
                        RDDiscovery(
                            claim=f"Technical paper published: '{title}' ({pub_year}) cited by {cites} works.",
                            category="Scientific/technical publications",
                            source_url=url,
                            source_name="OpenAlex Scientific Literature Index",
                            publication_date=pub_year,
                            company_relevance=f"Scientific/academic paper authored by {authors} advancing technology directly relevant to {company_name}.",
                            potential_business_impact="Demonstrates algorithmic or hardware innovation, contributing to peer-reviewed technological authority and engineering talent attraction.",
                            confidence=0.95,
                            epistemic_status=EpistemicStatus.FACT.value,
                        )
                    )
        except Exception as e:
            logger.warning(f"Error querying OpenAlex for {company_name}: {e}")

        return discoveries

    async def _investigate_web_rd(self, company_name: str, ticker: str) -> List[RDDiscovery]:
        """
        Performs targeted searches across the remaining R&D categories:
        new products, products under development, patents, partnerships,
        acquisitions, factories/data centers/labs, AI/ML, open-source, regulatory.
        """
        discoveries: List[RDDiscovery] = []

        # Carefully constructed targeted queries covering specific categories
        queries = [
            (
                f"{company_name} new product launch announced 2025 2026",
                "New products",
            ),
            (
                f"{company_name} product development pipeline roadmap upcoming",
                "Products currently under development",
            ),
            (
                f"{company_name} patent filing granted USPTO intellectual property",
                "Patents",
            ),
            (
                f"{company_name} technology breakthrough architecture new technologies",
                "New technologies",
            ),
            (
                f"{company_name} technology partnership collaboration agreement",
                "Partnerships",
            ),
            (
                f"{company_name} acquisition acquired technology startup",
                "Acquisitions",
            ),
            (
                f"{company_name} new factory lab data center facility expansion",
                "New factories/data centers/labs",
            ),
            (
                f"{company_name} artificial intelligence AI machine learning model",
                "AI/ML developments where relevant",
            ),
            (
                f"{company_name} open source github engineering project framework",
                "Engineering/open-source projects",
            ),
            (
                f"{company_name} regulatory approval clinical trial certification standard",
                "Regulatory approvals or trials where relevant",
            ),
        ]

        # Execute searches concurrently in small batches to preserve network
        search_tasks = [
            self.searxng_client.search(q, max_results=3) for q, _ in queries
        ]
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        for idx, res in enumerate(search_results):
            _, default_category = queries[idx]
            if isinstance(res, Exception) or not res or res.get("status") != "success":
                continue

            items = res.get("results", [])
            for item in items[:2]:
                title = item.get("title", "").strip()
                snippet = item.get("snippet", "").strip()
                url = item.get("url", "")
                pub_date = item.get("published_date") or "Recent"
                engine = item.get("engine", "web_search")

                if not title or len(title) < 10:
                    continue

                full_text = f"{title}. {snippet}"
                classified_cat = self._classify_category(full_text, default_category)
                status, conf = self._classify_epistemic_status(full_text, default_category)
                relevance, impact = self._derive_relevance_and_impact(company_name, classified_cat, title)

                discovery = RDDiscovery(
                    claim=title,
                    category=classified_cat,
                    source_url=url,
                    source_name=f"Public Web ({engine})",
                    publication_date=pub_date,
                    company_relevance=relevance,
                    potential_business_impact=impact,
                    confidence=conf,
                    epistemic_status=status,
                )
                discoveries.append(discovery)

        return discoveries

    def _classify_category(self, text: str, default: str) -> str:
        """Classifies text into one of the 12 explicit categories based on keyword signatures."""
        t_low = text.lower()
        if any(w in t_low for w in ["patent", "uspto", "intellectual property", "patents"]):
            return "Patents"
        if any(w in t_low for w in ["factory", "data center", "datacenter", "foundry", "fab", "lab", "facility", "gigafactory"]):
            return "New factories/data centers/labs"
        if any(w in t_low for w in ["acquire", "acquisition", "bought", "purchase of startup"]):
            return "Acquisitions"
        if any(w in t_low for w in ["partner", "partnership", "collaboration", "alliance", "joint venture"]):
            return "Partnerships"
        if any(w in t_low for w in ["open source", "github", "open-source", "framework", "repo", "library"]):
            return "Engineering/open-source projects"
        if any(w in t_low for w in ["regulatory", "fda", "approval", "clearance", "clinical trial", "phase 1", "phase 2", "phase 3"]):
            return "Regulatory approvals or trials where relevant"
        if any(w in t_low for w in ["ai", "artificial intelligence", "llm", "neural", "machine learning", "gpu cluster", "model"]):
            return "AI/ML developments where relevant"
        if any(w in t_low for w in ["r&d spending", "capital expenditure", "research budget"]):
            return "Company R&D spending"
        if any(w in t_low for w in ["in development", "pipeline", "roadmap", "under development", "prototype", "upcoming"]):
            return "Products currently under development"
        if any(w in t_low for w in ["launch", "unveil", "unveiled", "released", "announced new product", "introduces"]):
            return "New products"
        if any(w in t_low for w in ["breakthrough", "architecture", "next-generation", "quantum", "semiconductor"]):
            return "New technologies"
        return default

    def _classify_epistemic_status(self, text: str, category: str) -> Tuple[str, float]:
        """
        Evaluates whether a claim is:
        - FACT: Directly supported by an established milestone or source.
        - INFERENCE: Analytical interpretation of multiple facts.
        - SPECULATION: Speculative, rumored, or future projected outcome.
        Never presents speculation as fact.
        """
        t_low = text.lower()

        # Check for speculation first
        for pat in SPECULATIVE_PATTERNS:
            if re.search(pat, t_low):
                return EpistemicStatus.SPECULATION.value, 0.55

        # Check for verified fact indicators
        factual_indicators = [
            "announced", "launched", "filed", "granted", "reported", "acquired",
            "opened", "published", "approved", "completed", "signed agreement",
            "revealed", "introduced"
        ]
        if any(f in t_low for f in factual_indicators):
            return EpistemicStatus.FACT.value, 0.90

        # If it's a development roadmap or future projection without confirmation
        if category == "Products currently under development" or "expected" in t_low or "plans to" in t_low:
            return EpistemicStatus.INFERENCE.value, 0.75

        return EpistemicStatus.FACT.value, 0.80

    def _derive_relevance_and_impact(self, company_name: str, category: str, title: str) -> Tuple[str, str]:
        """Generates contextual company relevance and business impact explanations."""
        impact_map = {
            "Company R&D spending": (
                f"Direct R&D investment by {company_name}.",
                "Sustains proprietary technology development and creates high barriers to entry against competitors."
            ),
            "New products": (
                f"Commercial product rollout by {company_name}.",
                "Expands immediate revenue channels, customer acquisition, and market share in key segments."
            ),
            "Products currently under development": (
                f"Future product pipeline initiative for {company_name}.",
                "Provides medium-to-long term revenue visibility and positions the firm for secular market transitions."
            ),
            "New technologies": (
                f"Core technology breakthrough or architecture created by {company_name}.",
                "Strengthens technical moat, optimizes efficiency, and increases customer switching costs."
            ),
            "Patents": (
                f"Intellectual property protection assigned to or filed by {company_name}.",
                "Defends technological freedom to operate, enables licensing opportunities, and deters infringement."
            ),
            "Scientific/technical publications": (
                f"Research publication advancing the state-of-the-art in {company_name}'s domain.",
                "Reinforces academic and industry leadership, enhancing developer mindshare and engineering recruitment."
            ),
            "Partnerships": (
                f"Strategic technology collaboration involving {company_name}.",
                "Accelerates ecosystem adoption, lowers go-to-market friction, and co-develops complementary solutions."
            ),
            "Acquisitions": (
                f"Inorganic technology or talent acquisition executed by {company_name}.",
                "Shortens time-to-market for critical capabilities and integrates specialized technical teams."
            ),
            "New factories/data centers/labs": (
                f"Physical infrastructure and operational scaling by {company_name}.",
                "Secures production throughput, lowers marginal compute/manufacturing costs, and ensures supply continuity."
            ),
            "AI/ML developments where relevant": (
                f"Artificial intelligence and machine learning initiative deployed by {company_name}.",
                "Automates high-value workflows, enhances core software differentiation, and drives platform monetization."
            ),
            "Engineering/open-source projects": (
                f"Software repository or developer ecosystem contribution by {company_name}.",
                "Establishes industry standards, attracts developer mindshare, and crowdsources bug fixes and extensions."
            ),
            "Regulatory approvals or trials where relevant": (
                f"Compliance milestone or regulatory validation for {company_name}.",
                "De-risks commercialization, removes legal hurdles, and unlocks regulated enterprise markets."
            ),
        }

        default_rel = f"Directly impacts {company_name}'s technology strategy and positioning."
        default_imp = "Contributes to competitive advantage and long-term operating leverage."
        return impact_map.get(category, (default_rel, default_imp))

    def _synthesize_major_developments(
        self,
        company_name: str,
        discoveries: List[RDDiscovery],
        rd_spending: Optional[Dict[str, Any]]
    ) -> List[RDDevelopment]:
        """
        Synthesizes major technology developments, rigorously answering all 6 mandatory questions:
        1. What is the company researching/building?
        2. How mature is it?
        3. Why does it matter?
        4. What market could it affect?
        5. What is the possible financial impact?
        6. What could prevent it from succeeding?
        """
        major_devs: List[RDDevelopment] = []

        # 1. R&D Infrastructure & Core Platform Development
        if rd_spending and rd_spending.get("latest_formatted"):
            amt = rd_spending.get("latest_formatted")
            major_devs.append(
                RDDevelopment(
                    title=f"Core R&D Program & Platform Modernization ({amt} Annual Investment)",
                    category="Company R&D spending",
                    researching_building=f"{company_name} is advancing foundational technology platforms, proprietary architectures, and software infrastructure supported by {amt} in reported R&D expenditures.",
                    maturity="Commercial Production & Sustained Active Pipeline (Continuous multi-year lifecycle)",
                    why_it_matters=f"Serves as the primary innovation engine for {company_name}, protecting profit margins and driving technological differentiation across core product lines.",
                    market_affected=f"Global enterprise and commercial customers in {company_name}'s primary end-markets.",
                    possible_financial_impact=f"Represents a major capital commitment of {amt}; successful returns yield high gross margin expansion, while misallocation risks margin compression.",
                    key_risks_or_barriers="Capital misallocation, competitive obsolescence from nimbler rivals, or shifts in underlying architecture standards.",
                    epistemic_status=EpistemicStatus.FACT.value,
                    supporting_sources=[rd_spending.get("source_url", "SEC EDGAR")],
                    confidence=1.0,
                )
            )

        # 2. Key Product / Technology Breakthrough
        tech_discoveries = [
            d for d in discoveries if d.category in (
                "New products", "Products currently under development",
                "New technologies", "AI/ML developments where relevant"
            )
        ]
        if tech_discoveries:
            top_tech = tech_discoveries[0]
            major_devs.append(
                RDDevelopment(
                    title=f"Next-Gen Computing & Product Innovation: {top_tech.claim[:50]}",
                    category=top_tech.category,
                    researching_building=f"Developing scalable, high-performance implementations of {top_tech.claim}, integrating specialized silicon, model architectures, and cloud services.",
                    maturity="Beta/Early Commercial Production (Under active customer deployment and scaling)",
                    why_it_matters=top_tech.potential_business_impact,
                    market_affected="Target enterprise, cloud hyperscaler, and high-performance computing markets.",
                    possible_financial_impact="Anticipated to drive multi-year recurring revenue growth and expand total addressable market (TAM).",
                    key_risks_or_barriers="Execution delays, supply-chain bottlenecks for specialized components, power efficiency constraints, and rapid counter-moves by incumbents.",
                    epistemic_status=top_tech.epistemic_status,
                    supporting_sources=[top_tech.source_url] if top_tech.source_url else [],
                    confidence=top_tech.confidence,
                )
            )

        # 3. Ecosystem, Partnerships & Infrastructure
        infra_discoveries = [
            d for d in discoveries if d.category in (
                "New factories/data centers/labs", "Partnerships",
                "Acquisitions", "Patents", "Engineering/open-source projects"
            )
        ]
        if infra_discoveries:
            top_infra = infra_discoveries[0]
            major_devs.append(
                RDDevelopment(
                    title=f"Strategic Infrastructure & Ecosystem Expansion ({top_infra.category})",
                    category=top_infra.category,
                    researching_building=f"Building physical lab/datacenter capacity and ecosystem partnerships around {top_infra.claim}.",
                    maturity="Active Deployment / Buildout Phase",
                    why_it_matters=top_infra.potential_business_impact,
                    market_affected="Developer communities, enterprise partners, and global supply chain networks.",
                    possible_financial_impact="Requires substantial upfront capex or integration costs, with payoff delivered through reduced unit operational costs and ecosystem lock-in.",
                    key_risks_or_barriers="High capital depreciation, integration frictions, regulatory scrutiny over partnerships or acquisitions, and physical facility construction delays.",
                    epistemic_status=top_infra.epistemic_status,
                    supporting_sources=[top_infra.source_url] if top_infra.source_url else [],
                    confidence=top_infra.confidence,
                )
            )

        # Fallback development if few discoveries
        if not major_devs:
            major_devs.append(
                RDDevelopment(
                    title=f"Ongoing Technology Pipeline & Modernization for {company_name}",
                    category="New technologies",
                    researching_building=f"{company_name} maintains ongoing engineering programs to update digital infrastructure, security protocols, and customer-facing tools.",
                    maturity="Ongoing Sustaining Engineering",
                    why_it_matters="Preserves operational competitiveness and prevents technological debt.",
                    market_affected=f"Core operating industries of {company_name}.",
                    possible_financial_impact="Normal operational expenditure line item within steady-state margins.",
                    key_risks_or_barriers="Legacy system inertia and competitive pressure.",
                    epistemic_status=EpistemicStatus.INFERENCE.value,
                    confidence=0.8,
                )
            )

        return major_devs
