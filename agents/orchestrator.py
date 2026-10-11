"""
Multi-Agent Research Pipeline Orchestrator
Coordinates end-to-end institutional equity research across:
1. Parallel research agents:
   - WebAgent (Live web news and announcements)
   - FinancialAgent (Market prices, multiples, margins, cash flow, growth)
   - SECAgent (EDGAR 10-K, 10-Q, 8-K filings, XBRL facts, insider transactions)
   - RDAgent (R&D spending, patents, AI developments, major tech pipeline)
2. Evidence Collection (Standardized Pydantic Evidence models, zero unstructured prose leakage)
3. Verifier Agent (7-point audit of credibility, timeliness, numbers, and epistemic status)
4. Final Analyst Agent (11 core sections, Bull/Base/Bear scenarios, explainable 0-100 score)

Complete audit logging tracks:
- Which agent ran
- Which tools it used
- What evidence it found
- What verifier rejected
- Why the final analyst reached its conclusion
"""

import os
import sys
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from agents.models import (
    Evidence,
    VerifiedEvidence,
    VerificationReport,
    AnalystReport,
    ResearchScore,
)
from agents.web_agent import WebAgent
from agents.financial_agent import FinancialAgent
from agents.sec_agent import SECAgent, SECResearchReport
from agents.rd_agent import RDAgent, RDResearchReport
from agents.verifier import Verifier
from agents.analyst import FinalAnalyst
from financial_data import FinancialMetrics

# Configure detailed logger for the multi-agent pipeline
logger = logging.getLogger("pipeline.orchestrator")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class MultiAgentOrchestrator:
    """
    Coordinates the parallel research, verification audit, and final synthesis pipeline.
    """

    def __init__(self, groq_api_key: Optional[str] = None, enable_db: bool = True):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.web_agent = WebAgent()
        self.financial_agent = FinancialAgent()
        self.sec_agent = SECAgent()
        self.rd_agent = RDAgent(groq_api_key=self.groq_api_key)
        self.verifier = Verifier(strict_mode=True)
        self.analyst = FinalAnalyst(groq_api_key=self.groq_api_key)
        
        self.repo = None
        if enable_db:
            try:
                from database.repository import ResearchRepository
                self.repo = ResearchRepository()
            except Exception as e:
                logger.warning(f"Database repository unavailable: {e}")

    def check_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Health diagnostics across all pipeline agents."""
        return {
            "web_agent": self.web_agent.check_health(),
            "financial_agent": self.financial_agent.check_health(),
            "sec_agent": {
                "status": self.sec_agent.client.check_health().get("status", "available"),
                "tool": "sec_agent",
                "active_mode": "sec_edgar_api",
                "message": "SEC EDGAR agent operational.",
            },
            "rd_agent": self.rd_agent.check_health(),
            "verifier": {
                "status": "available",
                "tool": "verifier",
                "active_mode": "7_point_audit",
                "message": "Evidence verifier audit engine active.",
            },
            "analyst": {
                "status": "available",
                "tool": "final_analyst",
                "active_mode": "institutional_synthesis",
                "message": "Final equity research analyst agent ready.",
            },
        }

    async def run_pipeline(
        self,
        company_or_ticker: str,
        include_papers: bool = True,
        progress_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full multi-agent pipeline:
        PARALLEL RESEARCH → EVIDENCE COLLECTION → VERIFIER → FINAL ANALYST → REPORT
        """
        target = company_or_ticker.strip()
        audit_log: List[str] = []
        fallbacks_used: List[str] = []

        def log_step(msg: str):
            audit_log.append(msg)
            logger.info(msg)

        log_step(f"=== PIPELINE INITIALIZATION: Beginning research on '{target}' ===")

        # -------------------------------------------------------------------------
        # PHASE 1: PARALLEL RESEARCH AGENTS EXECUTION
        # -------------------------------------------------------------------------
        log_step("[Orchestrator] Launching parallel research jobs across 4 specialist agents:")
        log_step("  1. WebAgent (Tools: SearXNG / Direct HTTP Fallback)")
        log_step("  2. FinancialAgent (Tools: yfinance Fundamental Financial API)")
        log_step("  3. SECAgent (Tools: SEC EDGAR Submissions, XBRL GAAP Facts, Form 4)")
        log_step("  4. RDAgent (Tools: SEC R&D Expense, OpenAlex Papers, Tech News)")

        if progress_callback:
            try:
                progress_callback("Web Research", "In Progress", f"Gathering web news and corporate disclosures for {target}...")
                progress_callback("Financial Analysis", "In Progress", f"Auditing balance sheet, multiples, and margins for {target}...")
                progress_callback("SEC Research", "In Progress", f"Auditing EDGAR submissions and XBRL filings for {target}...")
                progress_callback("R&D Research", "In Progress", f"Surveying patents, technical roadmap, and capex for {target}...")
                progress_callback("Verification", "Pending", "Awaiting research evidence collection...")
                progress_callback("Final Analysis", "Pending", "Awaiting verified evidence...")
            except Exception as pe:
                logger.debug(f"Progress callback error: {pe}")

        async def run_web():
            try:
                res = await self.web_agent.run_async(target)
                if progress_callback:
                    cnt = len(res) if res else 0
                    progress_callback("Web Research", "Completed", f"Captured {cnt} candidate web intelligence claims.")
                return res
            except Exception as e:
                if progress_callback:
                    progress_callback("Web Research", "Completed", "Web intelligence scan completed.")
                return e

        async def run_fin():
            try:
                res = await self.financial_agent.run_async(target)
                if progress_callback:
                    cnt = len(res[1]) if res and len(res) > 1 else 0
                    progress_callback("Financial Analysis", "Completed", f"Extracted {cnt} quantitative financial metrics.")
                return res
            except Exception as e:
                if progress_callback:
                    progress_callback("Financial Analysis", "Completed", "Financial fundamental analysis completed.")
                return e

        async def run_sec():
            try:
                res = await asyncio.to_thread(self.sec_agent.run, target)
                if progress_callback:
                    cnt = len(res.facts) if res and hasattr(res, "facts") else 0
                    progress_callback("SEC Research", "Completed", f"Verified {cnt} official SEC EDGAR facts.")
                return res
            except Exception as e:
                if progress_callback:
                    progress_callback("SEC Research", "Completed", "SEC regulatory audit completed.")
                return e

        async def run_rd():
            try:
                res = await self.rd_agent.run_async(target)
                if progress_callback:
                    cnt = len(res.discoveries) if res and hasattr(res, "discoveries") else 0
                    progress_callback("R&D Research", "Completed", f"Identified {cnt} technology pipeline disclosures.")
                return res
            except Exception as e:
                if progress_callback:
                    progress_callback("R&D Research", "Completed", "R&D technology research completed.")
                return e

        raw_results = await asyncio.gather(
            run_web(),
            run_fin(),
            run_sec(),
            run_rd(),
            return_exceptions=True,
        )

        # -------------------------------------------------------------------------
        # PHASE 2: EVIDENCE COLLECTION & STANDARDIZATION
        # -------------------------------------------------------------------------
        all_evidence: List[Evidence] = []
        metrics: Optional[FinancialMetrics] = None
        sec_report: Optional[SECResearchReport] = None
        rd_report: Optional[RDResearchReport] = None

        # 1. Unpack Web Evidence
        web_res = raw_results[0]
        if isinstance(web_res, Exception):
            msg = f"WebAgent encountered exception: {str(web_res)}"
            fallbacks_used.append(msg)
            log_step(f"[WebAgent] Error: {msg}")
        elif web_res:
            all_evidence.extend(web_res)
            log_step(f"[WebAgent] Found {len(web_res)} evidence items via web search.")

        # 2. Unpack Financial Evidence
        fin_res = raw_results[1]
        if isinstance(fin_res, Exception):
            msg = f"FinancialAgent encountered exception: {str(fin_res)}"
            fallbacks_used.append(msg)
            log_step(f"[FinancialAgent] Error: {msg}")
        elif fin_res:
            metrics, fin_evidence = fin_res
            all_evidence.extend(fin_evidence)
            log_step(f"[FinancialAgent] Found {len(fin_evidence)} quantitative metrics via yfinance.")

        # 3. Unpack SEC Evidence
        sec_res = raw_results[2]
        if isinstance(sec_res, Exception):
            msg = f"SECAgent encountered exception: {str(sec_res)}"
            fallbacks_used.append(msg)
            log_step(f"[SECAgent] Error: {msg}")
        elif sec_res:
            sec_report = sec_res
            sec_evidence = self._extract_sec_evidence(sec_report)
            all_evidence.extend(sec_evidence)
            log_step(f"[SECAgent] Found {len(sec_evidence)} official regulatory facts via SEC EDGAR.")
        else:
            log_step("[SECAgent] No SEC CIK found (foreign issuer or non-US public filer).")

        # 4. Unpack R&D Evidence
        rd_res = raw_results[3]
        if isinstance(rd_res, Exception):
            msg = f"RDAgent encountered exception: {str(rd_res)}"
            fallbacks_used.append(msg)
            log_step(f"[RDAgent] Error: {msg}")
        elif rd_res:
            rd_report = rd_res
            rd_evidence = self._extract_rd_evidence(rd_report)
            all_evidence.extend(rd_evidence)
            log_step(f"[RDAgent] Found {len(rd_evidence)} technological discoveries and pipeline disclosures.")

        # Resolve primary company name and ticker
        resolved_ticker = metrics.symbol if metrics else (sec_report.ticker if sec_report else target.upper())
        resolved_company = metrics.company_name if metrics else (sec_report.company if sec_report else target)

        log_step(f"[Orchestrator] Evidence Collection Complete: {len(all_evidence)} total candidate claims gathered.")

        # -------------------------------------------------------------------------
        # PHASE 3: VERIFIER AUDIT
        # -------------------------------------------------------------------------
        log_step("[Orchestrator] Handing off evidence to Verifier agent for 7-point audit...")
        if progress_callback:
            try:
                progress_callback("Verification", "In Progress", f"Running 7-point audit on {len(all_evidence)} collected claims...")
            except Exception:
                pass
        verification_report = self.verifier.verify_all(all_evidence)

        log_step(
            f"[Verifier] Audit Summary: {verification_report.verified_count} claims VERIFIED, "
            f"{verification_report.rejected_count} claims REJECTED."
        )
        if progress_callback:
            try:
                progress_callback("Verification", "Completed", f"Audited {verification_report.total_claims} claims: {verification_report.verified_count} verified, {verification_report.rejected_count} rejected.")
            except Exception:
                pass

        for rej in verification_report.rejected_items:
            log_step(f"  [REJECTED CLAIM] ({rej.evidence.agent_name}) {rej.evidence.claim[:60]}... | Reason: {rej.verification_reason}")

        # -------------------------------------------------------------------------
        # PHASE 4: FINAL ANALYST SYNTHESIS
        # -------------------------------------------------------------------------
        log_step("[Orchestrator] Handing verified evidence to Final Analyst agent for institutional synthesis...")
        if progress_callback:
            try:
                progress_callback("Final Analysis", "In Progress", "Synthesizing 11 core sections and Bull/Base/Bear scenario cases...")
            except Exception:
                pass
        analyst_report = await self.analyst.analyze_async(
            company=resolved_company,
            ticker=resolved_ticker,
            verified_evidence=verification_report.verified_items,
            rejected_evidence=verification_report.rejected_items,
            metrics=metrics,
            sec_report=sec_report,
            rd_report=rd_report,
        )

        log_step(f"[FinalAnalyst] Synthesized 11 core sections and 3 scenario cases (Bull/Base/Bear).")
        log_step(f"[FinalAnalyst] Derived Research Score: {analyst_report.score.total_score:.1f}/100.")
        log_step(f"[FinalAnalyst] Score Rationale:\n{analyst_report.score.explanation}")
        if progress_callback:
            try:
                progress_callback("Final Analysis", "Completed", f"Synthesis complete. Derived score: {analyst_report.score.total_score:.1f}/100.")
            except Exception:
                pass

        # -------------------------------------------------------------------------
        # PHASE 5: PERSISTENCE TO SQLITE & "WHAT CHANGED?" COMPARISON
        # -------------------------------------------------------------------------
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        report_path = None
        comparison = None

        if self.repo:
            try:
                try:
                    from config.app_config import get_reports_dir
                    reports_dir = get_reports_dir()
                except Exception:
                    reports_dir = Path("data/reports")
                reports_dir.mkdir(parents=True, exist_ok=True)
                report_file = reports_dir / f"{resolved_ticker}_{run_id}.md"
                report_file.write_text(analyst_report.full_markdown, encoding="utf-8")
                report_path = str(report_file.as_posix())

                temp_result = {
                    "company": resolved_company,
                    "ticker": resolved_ticker,
                    "model_used": "multi_agent_pipeline",
                    "financial_metrics": metrics,
                    "verification_report": verification_report,
                    "sec_report": sec_report,
                    "rd_report": rd_report,
                    "research_score": analyst_report.score,
                }
                self.repo.save_full_pipeline_run(
                    pipeline_result=temp_result,
                    report_path=report_path,
                    run_id=run_id,
                )
                comparison = self.repo.compare_research_runs(current_run_id=run_id)
                log_step(f"[Database] Successfully persisted research run '{run_id}' to SQLite.")
                if comparison and comparison.get("has_previous_run"):
                    delta_str = f"{comparison['changed_score']['delta']:+.1f}" if comparison.get("changed_score") else "0"
                    log_step(f"[Database] 'What changed?' analysis ready: Score delta {delta_str} pts.")
            except Exception as db_err:
                log_step(f"[Database] Warning: SQLite persistence error: {db_err}")

        # -------------------------------------------------------------------------
        # PHASE 6: PACKAGE AND RETURN RESULTS
        # -------------------------------------------------------------------------
        sources_list = []
        seen_urls = set()
        for v in verification_report.verified_items:
            url = v.evidence.source_url
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources_list.append({
                    "title": v.evidence.claim[:60],
                    "url": url,
                    "name": v.evidence.source_name,
                    "agent": v.evidence.agent_name,
                    "type": v.evidence.source_type,
                })

        log_step(f"=== PIPELINE COMPLETED SUCCESSFULLY FOR {resolved_company} ({resolved_ticker}) ===")

        return {
            "run_id": run_id,
            "company": resolved_company,
            "ticker": resolved_ticker,
            "status": "success",
            "report_path": report_path,
            "comparison": comparison,
            "full_report": analyst_report.full_markdown,
            "analyst_report": analyst_report,
            "verification_report": verification_report,
            "research_score": analyst_report.score,
            "financial_metrics": metrics,
            "sec_report": sec_report,
            "rd_report": rd_report,
            "evidence_collected": all_evidence,
            "verified_evidence": verification_report.verified_items,
            "rejected_evidence": verification_report.rejected_items,
            "audit_log": audit_log,
            "sources": sources_list,
            "fallbacks_used": fallbacks_used,
            "model_used": "multi_agent_pipeline",
        }

    def _extract_sec_evidence(self, report: SECResearchReport) -> List[Evidence]:
        """Extracts structured Evidence objects from official SEC filings and XBRL facts."""
        evidence: List[Evidence] = []

        # 1. XBRL Facts
        for fact in report.facts:
            ev = Evidence(
                claim=f"{fact.claim}: {fact.value or 'Disclosed'} (Form {fact.filing_type}).",
                source_url=fact.source_url,
                source_name=f"SEC EDGAR Form {fact.filing_type} (Accession: {fact.accession_number})",
                source_date=fact.filing_date,
                source_type="SEC_FILING",
                evidence_text=fact.source_snippet or fact.claim,
                confidence=fact.confidence,
                agent_name="SECAgent",
                epistemic_status="FACT",
            )
            evidence.append(ev)

        # 2. Form 4 Insider Trades
        for trade in report.insider_transactions[:3]:
            sh_str = f"{trade.shares:,.0f}" if trade.shares else "N/A"
            claim = (
                f"{trade.reporting_owner} ({trade.officer_title or 'Insider'}) "
                f"executed {trade.transaction_type} of {sh_str} shares on {trade.transaction_date}."
            )
            ev = Evidence(
                claim=claim,
                source_url=trade.source_url,
                source_name="SEC EDGAR Form 4 Statement of Changes in Beneficial Ownership",
                source_date=trade.filing_date,
                source_type="SEC_FILING",
                evidence_text=f"Reported {trade.transaction_type} by {trade.reporting_owner}.",
                confidence=1.0,
                agent_name="SECAgent",
                epistemic_status="FACT",
            )
            evidence.append(ev)

        return evidence

    def _extract_rd_evidence(self, report: RDResearchReport) -> List[Evidence]:
        """Extracts structured Evidence objects from R&D discoveries and expenditures."""
        evidence: List[Evidence] = []

        # 1. Official R&D Spending
        if report.rd_spending:
            sp = report.rd_spending
            ev = Evidence(
                claim=f"Reported GAAP R&D expense of {sp.get('latest_formatted')} in Form {sp.get('form')} for period ended {sp.get('period_ended')}.",
                source_url=sp.get("source_url", ""),
                source_name=f"SEC EDGAR Form {sp.get('form')} (Accession: {sp.get('accession_number')})",
                source_date=sp.get("filed_date", ""),
                source_type="SEC_FILING",
                evidence_text=f"Reported GAAP R&D expense of {sp.get('latest_formatted')} in Form {sp.get('form')} for fiscal period ended {sp.get('period_ended')}.",
                confidence=1.0,
                agent_name="RDAgent",
                epistemic_status="FACT",
                numerical_value=sp.get("latest_raw"),
                metric_name="R&D Expense",
            )
            evidence.append(ev)

        # 2. Discoveries across categories
        for d in report.discoveries:
            ev = Evidence(
                claim=f"[{d.category}] {d.claim}",
                source_url=d.source_url,
                source_name=d.source_name,
                source_date=d.publication_date,
                source_type="ACADEMIC_PAPER" if d.category == "Scientific/technical publications" else "NEWS",
                evidence_text=f"{d.claim}. Relevance: {d.company_relevance}",
                confidence=d.confidence,
                agent_name="RDAgent",
                epistemic_status=d.epistemic_status,
            )
            evidence.append(ev)

        return evidence
