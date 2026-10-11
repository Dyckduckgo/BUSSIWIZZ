"""
Database Repository for StockResearchAgent
Encapsulates all database CRUD operations and analytical run comparisons.
Functions:
- create_company()
- get_company()
- create_research_run()
- save_evidence()
- save_metric()
- save_filing()
- save_rd_finding()
- save_score()
- get_previous_research_runs()
- compare_research_runs() (The "What changed?" engine)
"""

import uuid
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Generator

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.db import get_db_session, init_db
from database.models import (
    Company,
    ResearchRun,
    EvidenceItem,
    FinancialMetric,
    Filing,
    NewsArticle,
    RDProject,
    ScoreRecord,
)

logger = logging.getLogger("database.repository")


def utcnow() -> datetime:
    """Returns naive UTC datetime without deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ResearchRepository:
    """Repository instance managing database persistence and analysis comparison."""

    def __init__(self, session: Optional[Session] = None):
        self._external_session = session
        # Ensure database tables are created on first access
        try:
            init_db()
        except Exception as e:
            logger.warning(f"Database init check: {e}")

    @contextmanager
    def _session_scope(self, session: Optional[Session] = None) -> Generator[Session, None, None]:
        """
        Provides a safe session scope.
        If an external session is supplied, yields it without calling close() on exit.
        If no session is supplied, checks out a new session from get_db_session() which commits and closes.
        """
        target = session if session is not None else self._external_session
        if target is not None:
            yield target
            target.flush()
        else:
            with get_db_session() as s:
                yield s

    # -------------------------------------------------------------------------
    # 1. Company CRUD
    # -------------------------------------------------------------------------
    def create_company(
        self,
        ticker: str,
        name: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        cik: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Company:
        """Creates or updates a registered company."""
        clean_ticker = ticker.strip().upper()
        clean_name = name.strip()

        with self._session_scope(session) as s:
            company = s.query(Company).filter(Company.ticker == clean_ticker).first()
            if company:
                if clean_name and company.name != clean_name:
                    company.name = clean_name
                if sector:
                    company.sector = sector
                if industry:
                    company.industry = industry
                if cik:
                    company.cik = cik
                company.updated_at = utcnow()
                s.flush()
                return company

            company = Company(
                ticker=clean_ticker,
                name=clean_name or clean_ticker,
                sector=sector,
                industry=industry,
                cik=cik,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            s.add(company)
            s.flush()
            return company

    def get_company(
        self,
        ticker: str,
        session: Optional[Session] = None,
    ) -> Optional[Company]:
        """Retrieves a company by ticker symbol."""
        clean_ticker = ticker.strip().upper()
        with self._session_scope(session) as s:
            return s.query(Company).filter(Company.ticker == clean_ticker).first()

    # -------------------------------------------------------------------------
    # 2. Research Run CRUD
    # -------------------------------------------------------------------------
    def create_research_run(
        self,
        company_id_or_ticker: Union[int, str],
        run_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        completion_time: Optional[datetime] = None,
        final_score: Optional[float] = None,
        report_path: Optional[str] = None,
        status: str = "COMPLETED",
        model_used: str = "multi_agent_pipeline",
        company_name: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> ResearchRun:
        """
        Creates and registers an individual research run.
        Attributes: run ID, company, start time, completion time, final score, report path.
        """
        resolved_run_id = run_id or f"run_{uuid.uuid4().hex[:12]}"
        st_time = start_time or utcnow()

        with self._session_scope(session) as s:
            if isinstance(company_id_or_ticker, int):
                company = s.query(Company).filter(Company.id == company_id_or_ticker).first()
                if not company:
                    raise ValueError(f"Company ID {company_id_or_ticker} not found.")
            else:
                ticker = str(company_id_or_ticker).strip().upper()
                company = s.query(Company).filter(Company.ticker == ticker).first()
                if not company:
                    company = self.create_company(
                        ticker=ticker,
                        name=company_name or ticker,
                        session=s,
                    )

            # Check if run already exists
            existing_run = s.query(ResearchRun).filter(ResearchRun.run_id == resolved_run_id).first()
            if existing_run:
                existing_run.completion_time = completion_time or utcnow()
                if final_score is not None:
                    existing_run.final_score = final_score
                if report_path:
                    existing_run.report_path = report_path
                existing_run.status = status
                s.flush()
                return existing_run

            run = ResearchRun(
                run_id=resolved_run_id,
                company_id=company.id,
                company_ticker=company.ticker,
                start_time=st_time,
                completion_time=completion_time,
                final_score=final_score,
                report_path=report_path,
                status=status,
                model_used=model_used,
            )
            s.add(run)
            s.flush()
            return run

    # -------------------------------------------------------------------------
    # 3. Evidence Persistence
    # -------------------------------------------------------------------------
    def save_evidence(
        self,
        run_id: str,
        claim: str,
        source_url: str = "",
        source_name: str = "",
        source_date: str = "",
        source_type: str = "NEWS",
        agent: str = "",
        confidence: float = 0.8,
        verified_status: bool = True,
        verification_reason: str = "",
        timestamp: Optional[datetime] = None,
        epistemic_status: str = "FACT",
        category: str = "",
        numerical_value: Optional[float] = None,
        metric_name: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> EvidenceItem:
        """
        Stores an evidence item retaining claim, source URL, date, type, agent,
        confidence, verified status, verification reason, and timestamp.
        """
        with self._session_scope(session) as s:
            run = s.query(ResearchRun).filter(ResearchRun.run_id == run_id).first()
            company_id = run.company_id if run else None

            ev_item = EvidenceItem(
                run_id=run_id,
                company_id=company_id,
                claim=claim.strip(),
                source_url=source_url or "",
                source_name=source_name or "",
                source_date=source_date or "",
                source_type=source_type or "NEWS",
                agent=agent or "Agent",
                confidence=float(confidence) if confidence is not None else 0.8,
                verified_status=bool(verified_status),
                verification_reason=verification_reason or "",
                timestamp=timestamp or utcnow(),
                epistemic_status=epistemic_status or "FACT",
                category=category or "",
                numerical_value=numerical_value,
                metric_name=metric_name,
            )
            s.add(ev_item)
            s.flush()
            return ev_item

    # -------------------------------------------------------------------------
    # 4. Financial Metric Persistence
    # -------------------------------------------------------------------------
    def save_metric(
        self,
        run_id: str,
        metric_name: str,
        metric_value: Optional[float] = None,
        metric_text: Optional[str] = None,
        period: str = "TTM",
        data_source: str = "yfinance",
        session: Optional[Session] = None,
    ) -> FinancialMetric:
        """Saves a quantitative financial metric snapshot."""
        with self._session_scope(session) as s:
            run = s.query(ResearchRun).filter(ResearchRun.run_id == run_id).first()
            company_id = run.company_id if run else None

            val = float(metric_value) if metric_value is not None else None
            metric = FinancialMetric(
                run_id=run_id,
                company_id=company_id,
                metric_name=metric_name.strip(),
                metric_value=val,
                metric_text=str(metric_text) if metric_text is not None else None,
                period=period or "TTM",
                data_source=data_source or "yfinance",
                timestamp=utcnow(),
            )
            s.add(metric)
            s.flush()
            return metric

    # -------------------------------------------------------------------------
    # 5. Regulatory Filing Persistence
    # -------------------------------------------------------------------------
    def save_filing(
        self,
        run_id: str,
        form_type: str,
        filing_date: str = "",
        accession_number: str = "",
        source_url: str = "",
        description: str = "",
        facts_count: int = 0,
        session: Optional[Session] = None,
    ) -> Filing:
        """Saves a regulatory SEC filing record."""
        with self._session_scope(session) as s:
            run = s.query(ResearchRun).filter(ResearchRun.run_id == run_id).first()
            company_id = run.company_id if run else None

            filing = Filing(
                run_id=run_id,
                company_id=company_id,
                form_type=form_type.strip(),
                filing_date=filing_date or "",
                accession_number=accession_number or "",
                source_url=source_url or "",
                description=description or "",
                facts_count=int(facts_count) if facts_count else 0,
                timestamp=utcnow(),
            )
            s.add(filing)
            s.flush()
            return filing

    # -------------------------------------------------------------------------
    # 6. R&D Finding Persistence
    # -------------------------------------------------------------------------
    def save_rd_finding(
        self,
        run_id: str,
        title: str,
        category: str = "New products",
        description: str = "",
        maturity: str = "",
        potential_impact: str = "",
        source_url: str = "",
        session: Optional[Session] = None,
    ) -> RDProject:
        """Saves an R&D breakthrough, patent, paper, or technology pipeline finding."""
        with self._session_scope(session) as s:
            run = s.query(ResearchRun).filter(ResearchRun.run_id == run_id).first()
            company_id = run.company_id if run else None

            project = RDProject(
                run_id=run_id,
                company_id=company_id,
                title=title.strip(),
                category=category or "New products",
                description=description or "",
                maturity=maturity or "",
                potential_impact=potential_impact or "",
                source_url=source_url or "",
                timestamp=utcnow(),
            )
            s.add(project)
            s.flush()
            return project

    # -------------------------------------------------------------------------
    # 7. Score Persistence
    # -------------------------------------------------------------------------
    def save_score(
        self,
        run_id: str,
        total_score: float,
        business_quality: float = 0.0,
        financial_health: float = 0.0,
        growth: float = 0.0,
        competitive_advantage: float = 0.0,
        valuation: float = 0.0,
        rd_innovation: float = 0.0,
        risk_profile: float = 0.0,
        explanation: str = "",
        disclaimer: str = "",
        session: Optional[Session] = None,
    ) -> ScoreRecord:
        """Saves explainable institutional score and updates research run."""
        with self._session_scope(session) as s:
            run = s.query(ResearchRun).filter(ResearchRun.run_id == run_id).first()
            company_id = run.company_id if run else None

            tot = round(float(total_score), 1)
            score_rec = ScoreRecord(
                run_id=run_id,
                company_id=company_id,
                total_score=tot,
                business_quality=round(float(business_quality), 1),
                financial_health=round(float(financial_health), 1),
                growth=round(float(growth), 1),
                competitive_advantage=round(float(competitive_advantage), 1),
                valuation=round(float(valuation), 1),
                rd_innovation=round(float(rd_innovation), 1),
                risk_profile=round(float(risk_profile), 1),
                explanation=explanation or "",
                disclaimer=disclaimer or "",
                timestamp=utcnow(),
            )
            s.add(score_rec)

            if run:
                run.final_score = tot

            s.flush()
            return score_rec

    # -------------------------------------------------------------------------
    # 8. Query Historical Research Runs
    # -------------------------------------------------------------------------
    def get_previous_research_runs(
        self,
        company_or_ticker: str,
        limit: int = 10,
        session: Optional[Session] = None,
    ) -> List[ResearchRun]:
        """Retrieves prior completed research runs for a company, most recent first."""
        clean_target = company_or_ticker.strip().upper()
        with self._session_scope(session) as s:
            query = (
                s.query(ResearchRun)
                .join(Company, ResearchRun.company_id == Company.id)
                .filter((Company.ticker == clean_target) | (Company.name.ilike(f"%{clean_target}%")))
                .order_by(desc(ResearchRun.start_time))
                .limit(limit)
            )
            return query.all()

    # -------------------------------------------------------------------------
    # 9. "What changed?" Comparative Intelligence Engine
    # -------------------------------------------------------------------------
    def compare_research_runs(
        self,
        current_run_id: str,
        previous_run_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Analyzes delta between two research runs for the same company.
        Identifies:
        - new developments
        - removed/invalidated claims
        - changed financial metrics
        - changed risks
        - changed R&D findings
        - changed score
        """
        with self._session_scope(session) as s:
            curr_run = s.query(ResearchRun).filter(ResearchRun.run_id == current_run_id).first()
            if not curr_run:
                raise ValueError(f"Current research run '{current_run_id}' not found.")

            # Automatically locate previous run for the same company if not explicitly specified
            if previous_run_id:
                prev_run = s.query(ResearchRun).filter(ResearchRun.run_id == previous_run_id).first()
                if not prev_run:
                    raise ValueError(f"Previous research run '{previous_run_id}' not found.")
            else:
                prev_run = (
                    s.query(ResearchRun)
                    .filter(
                        ResearchRun.company_id == curr_run.company_id,
                        ResearchRun.run_id != curr_run.run_id,
                        ResearchRun.start_time < curr_run.start_time,
                    )
                    .order_by(desc(ResearchRun.start_time))
                    .first()
                )

            # If no previous run exists, return baseline status
            if not prev_run:
                return {
                    "has_previous_run": False,
                    "company": curr_run.company.name if curr_run.company else curr_run.company_ticker,
                    "ticker": curr_run.company_ticker,
                    "current_run_id": curr_run.run_id,
                    "current_date": curr_run.start_time.strftime("%Y-%m-%d %H:%M"),
                    "current_score": curr_run.final_score,
                    "message": "Baseline research run. No previous research found for historical comparison.",
                    "changed_score": None,
                    "changed_financial_metrics": [],
                    "new_developments": [],
                    "removed_or_invalidated_claims": [],
                    "changed_risks": [],
                    "changed_rd_findings": [],
                    "summary_text": f"Baseline research execution on {curr_run.company_ticker}. Score: {curr_run.final_score}/100.",
                }

            # -----------------------------------------------------------------
            # 1. Compare Scores
            # -----------------------------------------------------------------
            curr_score_rec = s.query(ScoreRecord).filter(ScoreRecord.run_id == curr_run.run_id).first()
            prev_score_rec = s.query(ScoreRecord).filter(ScoreRecord.run_id == prev_run.run_id).first()

            curr_total = curr_score_rec.total_score if curr_score_rec else (curr_run.final_score or 0.0)
            prev_total = prev_score_rec.total_score if prev_score_rec else (prev_run.final_score or 0.0)
            score_delta = round(curr_total - prev_total, 1)

            dimension_changes = {}
            if curr_score_rec and prev_score_rec:
                dims = [
                    ("business_quality", "Business Quality (0-20)"),
                    ("financial_health", "Financial Health (0-20)"),
                    ("growth", "Growth (0-15)"),
                    ("competitive_advantage", "Competitive Advantage (0-15)"),
                    ("valuation", "Valuation (0-15)"),
                    ("rd_innovation", "R&D / Innovation (0-10)"),
                    ("risk_profile", "Risk Profile (0-5)"),
                ]
                for attr, label in dims:
                    c_val = getattr(curr_score_rec, attr, 0.0) or 0.0
                    p_val = getattr(prev_score_rec, attr, 0.0) or 0.0
                    dimension_changes[label] = {
                        "previous": p_val,
                        "current": c_val,
                        "delta": round(c_val - p_val, 1),
                    }

            changed_score = {
                "previous_score": prev_total,
                "current_score": curr_total,
                "delta": score_delta,
                "dimension_changes": dimension_changes,
                "explanation": (
                    f"Research score changed by {score_delta:+.1f} points "
                    f"({prev_total} → {curr_total})."
                ),
            }

            # -----------------------------------------------------------------
            # 2. Compare Financial Metrics
            # -----------------------------------------------------------------
            curr_metrics = {
                m.metric_name: m for m in s.query(FinancialMetric).filter(FinancialMetric.run_id == curr_run.run_id).all()
            }
            prev_metrics = {
                m.metric_name: m for m in s.query(FinancialMetric).filter(FinancialMetric.run_id == prev_run.run_id).all()
            }

            changed_financial_metrics: List[Dict[str, Any]] = []
            all_metric_keys = sorted(set(curr_metrics.keys()) | set(prev_metrics.keys()))

            for m_key in all_metric_keys:
                c_m = curr_metrics.get(m_key)
                p_m = prev_metrics.get(m_key)

                c_val = c_m.metric_value if c_m else None
                p_val = p_m.metric_value if p_m else None
                c_txt = c_m.metric_text if c_m else "N/A"
                p_txt = p_m.metric_text if p_m else "N/A"

                is_changed = False
                delta = None
                direction = "unchanged"

                if c_val is not None and p_val is not None:
                    if abs(c_val - p_val) > 0.0001:
                        is_changed = True
                        delta = round(c_val - p_val, 4)
                        direction = "increased" if delta > 0 else "decreased"
                elif c_txt != p_txt:
                    is_changed = True
                    direction = "new" if p_val is None else "removed"

                if is_changed:
                    changed_financial_metrics.append({
                        "metric": m_key,
                        "previous_value": p_val,
                        "current_value": c_val,
                        "previous_text": p_txt,
                        "current_text": c_txt,
                        "delta": delta,
                        "direction": direction,
                    })

            # -----------------------------------------------------------------
            # 3. Evidence Comparison (New developments, removed claims, risks)
            # -----------------------------------------------------------------
            curr_evidence = s.query(EvidenceItem).filter(EvidenceItem.run_id == curr_run.run_id).all()
            prev_evidence = s.query(EvidenceItem).filter(EvidenceItem.run_id == prev_run.run_id).all()

            prev_claims_set = {ev.claim.strip().lower() for ev in prev_evidence if ev.verified_status}
            curr_claims_set = {ev.claim.strip().lower() for ev in curr_evidence if ev.verified_status}

            # New Developments: Verified claims or news in current run not present in previous run
            new_developments: List[Dict[str, Any]] = []
            for ev in curr_evidence:
                if ev.verified_status and ev.claim.strip().lower() not in prev_claims_set:
                    new_developments.append({
                        "claim": ev.claim,
                        "agent": ev.agent,
                        "source": ev.source_name or ev.source_type,
                        "url": ev.source_url,
                        "date": ev.source_date,
                    })

            # Removed/Invalidated Claims: Claims verified previously but now rejected or missing
            removed_or_invalidated_claims: List[Dict[str, Any]] = []
            # Explicitly rejected in current run
            for ev in curr_evidence:
                if not ev.verified_status:
                    removed_or_invalidated_claims.append({
                        "claim": ev.claim,
                        "agent": ev.agent,
                        "status": "REJECTED_BY_VERIFIER",
                        "reason": ev.verification_reason,
                    })
            # Verified previously but missing now
            for ev in prev_evidence:
                if ev.verified_status and ev.claim.strip().lower() not in curr_claims_set:
                    if not any(r["claim"] == ev.claim for r in removed_or_invalidated_claims):
                        removed_or_invalidated_claims.append({
                            "claim": ev.claim,
                            "agent": ev.agent,
                            "status": "NOT_RE-VERIFIED_OR_SUPERSEDED",
                            "reason": "Previous claim no longer asserted or substantiated in current filing/news cycle.",
                        })

            # Changed Risks: Claims or evidence highlighting threats, headwinds, risks
            changed_risks: List[Dict[str, Any]] = []
            risk_keywords = ["risk", "threat", "headwind", "restriction", "sanction", "decline", "pressure", "slowdown", "bottleneck"]
            for ev in curr_evidence:
                c_low = ev.claim.lower()
                if any(kw in c_low for kw in risk_keywords) or ev.category == "risks":
                    is_new = ev.claim.strip().lower() not in prev_claims_set
                    changed_risks.append({
                        "claim": ev.claim,
                        "agent": ev.agent,
                        "verified": ev.verified_status,
                        "is_new_risk": is_new,
                        "source": ev.source_name,
                    })

            # -----------------------------------------------------------------
            # 4. Compare R&D Findings
            # -----------------------------------------------------------------
            curr_rd = s.query(RDProject).filter(RDProject.run_id == curr_run.run_id).all()
            prev_rd = s.query(RDProject).filter(RDProject.run_id == prev_run.run_id).all()
            prev_rd_titles = {p.title.strip().lower() for p in prev_rd}

            changed_rd_findings: List[Dict[str, Any]] = []
            for p in curr_rd:
                is_new = p.title.strip().lower() not in prev_rd_titles
                changed_rd_findings.append({
                    "title": p.title,
                    "category": p.category,
                    "maturity": p.maturity,
                    "potential_impact": p.potential_impact,
                    "is_new_discovery": is_new,
                })

            # -----------------------------------------------------------------
            # 5. Build Human-Readable Narrative Summary
            # -----------------------------------------------------------------
            summary_lines = [
                f"# What Changed: {curr_run.company.name if curr_run.company else curr_run.company_ticker} ({curr_run.company_ticker})",
                f"**Comparison Window**: Previous Run `{prev_run.run_id}` ({prev_run.start_time.strftime('%Y-%m-%d')}) → Current Run `{curr_run.run_id}` ({curr_run.start_time.strftime('%Y-%m-%d')})",
                "",
                f"### 1. Research Score Delta: {score_delta:+.1f} Points",
                f"- **Previous Score**: {prev_total:.1f} / 100",
                f"- **Current Score**: {curr_total:.1f} / 100",
            ]

            if dimension_changes:
                for dim, vals in dimension_changes.items():
                    if abs(vals["delta"]) > 0.0:
                        summary_lines.append(f"  - {dim}: {vals['previous']} → {vals['current']} ({vals['delta']:+.1f})")

            if changed_financial_metrics:
                summary_lines.append("\n### 2. Changed Financial Metrics")
                for cm in changed_financial_metrics[:8]:
                    summary_lines.append(f"- **{cm['metric']}**: {cm['previous_text']} → {cm['current_text']} ({cm['direction']})")

            if new_developments:
                summary_lines.append("\n### 3. New Developments")
                for nd in new_developments[:5]:
                    summary_lines.append(f"- [{nd['agent']}] {nd['claim']}")

            if removed_or_invalidated_claims:
                summary_lines.append("\n### 4. Removed or Invalidated Claims")
                for rc in removed_or_invalidated_claims[:5]:
                    summary_lines.append(f"- [{rc['status']}] {rc['claim'][:80]}... (Reason: {rc['reason'][:80]})")

            if changed_risks:
                summary_lines.append("\n### 5. Identified Risk Headwinds")
                for cr in changed_risks[:4]:
                    tag = "NEW RISK" if cr["is_new_risk"] else "PERSISTING RISK"
                    summary_lines.append(f"- [{tag}] {cr['claim']}")

            if changed_rd_findings:
                summary_lines.append("\n### 6. R&D Pipeline & Breakthroughs")
                for crd in changed_rd_findings[:4]:
                    tag = "NEW BREAKTHROUGH" if crd["is_new_discovery"] else "PIPELINE UPDATE"
                    summary_lines.append(f"- [{tag}] **{crd['title']}** ({crd['category']}): {crd['potential_impact'][:80]}")

            summary_text = "\n".join(summary_lines)

            return {
                "has_previous_run": True,
                "company": curr_run.company.name if curr_run.company else curr_run.company_ticker,
                "ticker": curr_run.company_ticker,
                "current_run_id": curr_run.run_id,
                "previous_run_id": prev_run.run_id,
                "current_date": curr_run.start_time.strftime("%Y-%m-%d %H:%M"),
                "previous_date": prev_run.start_time.strftime("%Y-%m-%d %H:%M"),
                "changed_score": changed_score,
                "changed_financial_metrics": changed_financial_metrics,
                "new_developments": new_developments,
                "removed_or_invalidated_claims": removed_or_invalidated_claims,
                "changed_risks": changed_risks,
                "changed_rd_findings": changed_rd_findings,
                "summary_text": summary_text,
            }

    # -------------------------------------------------------------------------
    # 10. Pipeline Integration Helper
    # -------------------------------------------------------------------------
    def save_full_pipeline_run(
        self,
        pipeline_result: Dict[str, Any],
        report_path: Optional[str] = None,
        run_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> ResearchRun:
        """
        Seamlessly persists an entire multi-agent pipeline output dictionary:
        - Company
        - ResearchRun
        - Evidence items (both verified and rejected)
        - Financial metrics
        - SEC filings
        - R&D findings & spending
        - Scores
        """
        ticker = pipeline_result.get("ticker", "UNKNOWN").upper()
        company_name = pipeline_result.get("company", ticker)
        score_obj = pipeline_result.get("research_score")
        total_score = score_obj.total_score if score_obj else 0.0

        with self._session_scope(session) as s:
            # 1. Company
            company = self.create_company(ticker=ticker, name=company_name, session=s)

            # 2. ResearchRun
            run = self.create_research_run(
                company_id_or_ticker=company.id,
                run_id=run_id,
                completion_time=utcnow(),
                final_score=total_score,
                report_path=report_path,
                model_used=pipeline_result.get("model_used", "multi_agent_pipeline"),
                session=s,
            )

            # 3. Financial Metrics
            metrics = pipeline_result.get("financial_metrics")
            if metrics:
                summary = metrics.to_summary_dict() if hasattr(metrics, "to_summary_dict") else {}
                metric_pairs = [
                    ("Current Price", metrics.current_price, summary.get("Current Price")),
                    ("Market Cap", metrics.market_cap, summary.get("Market Cap")),
                    ("Revenue", metrics.revenue, summary.get("Revenue (TTM)")),
                    ("Net Income", metrics.net_income, summary.get("Net Income (TTM)")),
                    ("Diluted EPS", metrics.eps, summary.get("Diluted EPS")),
                    ("Gross Margin", metrics.gross_margin, summary.get("Gross Margin")),
                    ("Operating Margin", metrics.operating_margin, summary.get("Operating Margin")),
                    ("Free Cash Flow", metrics.free_cash_flow, summary.get("Free Cash Flow")),
                    ("Total Cash", metrics.cash, summary.get("Total Cash")),
                    ("Total Debt", metrics.debt, summary.get("Total Debt")),
                    ("P/E Ratio", metrics.pe_ratio, summary.get("P/E Ratio")),
                    ("P/S Ratio", metrics.ps_ratio, summary.get("P/S Ratio")),
                    ("EV/EBITDA", metrics.ev_ebitda, summary.get("EV/EBITDA")),
                    ("Revenue Growth (YoY)", metrics.revenue_growth, summary.get("Revenue Growth (YoY)")),
                    ("EPS Growth (YoY)", metrics.eps_growth, summary.get("EPS Growth (YoY)")),
                ]
                for name, val, txt in metric_pairs:
                    if val is not None or txt is not None:
                        self.save_metric(
                            run_id=run.run_id,
                            metric_name=name,
                            metric_value=val,
                            metric_text=txt,
                            data_source="yfinance",
                            session=s,
                        )

            # 4. Evidence (Verified and Rejected)
            ver_report = pipeline_result.get("verification_report")
            if ver_report:
                for item in getattr(ver_report, "verified_items", []):
                    ev = item.evidence
                    self.save_evidence(
                        run_id=run.run_id,
                        claim=ev.claim,
                        source_url=ev.source_url,
                        source_date=ev.source_date,
                        source_type=ev.source_type,
                        agent=ev.agent_name,
                        confidence=ev.confidence,
                        verified_status=True,
                        verification_reason=item.verification_reason,
                        epistemic_status=ev.epistemic_status,
                        numerical_value=ev.numerical_value,
                        metric_name=ev.metric_name,
                        session=s,
                    )
                for item in getattr(ver_report, "rejected_items", []):
                    ev = item.evidence
                    self.save_evidence(
                        run_id=run.run_id,
                        claim=ev.claim,
                        source_url=ev.source_url,
                        source_date=ev.source_date,
                        source_type=ev.source_type,
                        agent=ev.agent_name,
                        confidence=ev.confidence,
                        verified_status=False,
                        verification_reason=item.verification_reason,
                        epistemic_status=ev.epistemic_status,
                        numerical_value=ev.numerical_value,
                        metric_name=ev.metric_name,
                        session=s,
                    )

            # 5. SEC Filings
            sec_report = pipeline_result.get("sec_report")
            if sec_report and hasattr(sec_report, "facts"):
                seen_forms = set()
                for fact in sec_report.facts:
                    form_key = (fact.filing_type, fact.accession_number)
                    if form_key not in seen_forms:
                        seen_forms.add(form_key)
                        self.save_filing(
                            run_id=run.run_id,
                            form_type=fact.filing_type,
                            filing_date=fact.filing_date,
                            accession_number=fact.accession_number,
                            source_url=fact.source_url,
                            description=f"XBRL Financial Fact: {fact.claim}",
                            facts_count=len(sec_report.facts),
                            session=s,
                        )

            # 6. R&D Projects & Spending
            rd_report = pipeline_result.get("rd_report")
            if rd_report:
                if hasattr(rd_report, "major_developments"):
                    for dev in rd_report.major_developments:
                        self.save_rd_finding(
                            run_id=run.run_id,
                            title=dev.title,
                            category=dev.category,
                            description=dev.researching_building,
                            maturity=dev.maturity,
                            potential_impact=dev.possible_financial_impact,
                            source_url=dev.supporting_sources[0] if dev.supporting_sources else "",
                            session=s,
                        )
                if hasattr(rd_report, "rd_spending") and rd_report.rd_spending:
                    sp = rd_report.rd_spending
                    self.save_rd_finding(
                        run_id=run.run_id,
                        title=f"GAAP R&D Expenditure ({sp.get('latest_formatted')})",
                        category="Company R&D spending",
                        description=f"Reported in SEC Form {sp.get('form')} for fiscal period {sp.get('period_ended')}.",
                        maturity="Reported Capital Allocation",
                        potential_impact=f"Annual research reinvestment of {sp.get('latest_formatted')}.",
                        source_url=sp.get("source_url", ""),
                        session=s,
                    )

            # 7. Score
            if score_obj:
                self.save_score(
                    run_id=run.run_id,
                    total_score=score_obj.total_score,
                    business_quality=score_obj.business_quality,
                    financial_health=score_obj.financial_health,
                    growth=score_obj.growth,
                    competitive_advantage=score_obj.competitive_advantage,
                    valuation=score_obj.valuation,
                    rd_innovation=score_obj.rd_innovation,
                    risk_profile=score_obj.risk_profile,
                    explanation=score_obj.explanation,
                    disclaimer=score_obj.disclaimer,
                    session=s,
                )

            s.flush()
            return run


# -----------------------------------------------------------------------------
# Module-level convenience functions matching explicit user prompt signatures
# -----------------------------------------------------------------------------
_repo = ResearchRepository()


def create_company(
    ticker: str,
    name: str,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    cik: Optional[str] = None,
    session: Optional[Session] = None,
) -> Company:
    return _repo.create_company(
        ticker=ticker,
        name=name,
        sector=sector,
        industry=industry,
        cik=cik,
        session=session,
    )


def get_company(
    ticker: str,
    session: Optional[Session] = None,
) -> Optional[Company]:
    return _repo.get_company(ticker=ticker, session=session)


def create_research_run(
    company_id_or_ticker: Union[int, str],
    run_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    completion_time: Optional[datetime] = None,
    final_score: Optional[float] = None,
    report_path: Optional[str] = None,
    status: str = "COMPLETED",
    model_used: str = "multi_agent_pipeline",
    company_name: Optional[str] = None,
    session: Optional[Session] = None,
) -> ResearchRun:
    return _repo.create_research_run(
        company_id_or_ticker=company_id_or_ticker,
        run_id=run_id,
        start_time=start_time,
        completion_time=completion_time,
        final_score=final_score,
        report_path=report_path,
        status=status,
        model_used=model_used,
        company_name=company_name,
        session=session,
    )


def save_evidence(
    run_id: str,
    claim: str,
    source_url: str = "",
    source_name: str = "",
    source_date: str = "",
    source_type: str = "NEWS",
    agent: str = "",
    confidence: float = 0.8,
    verified_status: bool = True,
    verification_reason: str = "",
    timestamp: Optional[datetime] = None,
    epistemic_status: str = "FACT",
    category: str = "",
    numerical_value: Optional[float] = None,
    metric_name: Optional[str] = None,
    session: Optional[Session] = None,
) -> EvidenceItem:
    return _repo.save_evidence(
        run_id=run_id,
        claim=claim,
        source_url=source_url,
        source_name=source_name,
        source_date=source_date,
        source_type=source_type,
        agent=agent,
        confidence=confidence,
        verified_status=verified_status,
        verification_reason=verification_reason,
        timestamp=timestamp,
        epistemic_status=epistemic_status,
        category=category,
        numerical_value=numerical_value,
        metric_name=metric_name,
        session=session,
    )


def save_metric(
    run_id: str,
    metric_name: str,
    metric_value: Optional[float] = None,
    metric_text: Optional[str] = None,
    period: str = "TTM",
    data_source: str = "yfinance",
    session: Optional[Session] = None,
) -> FinancialMetric:
    return _repo.save_metric(
        run_id=run_id,
        metric_name=metric_name,
        metric_value=metric_value,
        metric_text=metric_text,
        period=period,
        data_source=data_source,
        session=session,
    )


def save_filing(
    run_id: str,
    form_type: str,
    filing_date: str = "",
    accession_number: str = "",
    source_url: str = "",
    description: str = "",
    facts_count: int = 0,
    session: Optional[Session] = None,
) -> Filing:
    return _repo.save_filing(
        run_id=run_id,
        form_type=form_type,
        filing_date=filing_date,
        accession_number=accession_number,
        source_url=source_url,
        description=description,
        facts_count=facts_count,
        session=session,
    )


def save_rd_finding(
    run_id: str,
    title: str,
    category: str = "New products",
    description: str = "",
    maturity: str = "",
    potential_impact: str = "",
    source_url: str = "",
    session: Optional[Session] = None,
) -> RDProject:
    return _repo.save_rd_finding(
        run_id=run_id,
        title=title,
        category=category,
        description=description,
        maturity=maturity,
        potential_impact=potential_impact,
        source_url=source_url,
        session=session,
    )


def save_score(
    run_id: str,
    total_score: float,
    business_quality: float = 0.0,
    financial_health: float = 0.0,
    growth: float = 0.0,
    competitive_advantage: float = 0.0,
    valuation: float = 0.0,
    rd_innovation: float = 0.0,
    risk_profile: float = 0.0,
    explanation: str = "",
    disclaimer: str = "",
    session: Optional[Session] = None,
) -> ScoreRecord:
    return _repo.save_score(
        run_id=run_id,
        total_score=total_score,
        business_quality=business_quality,
        financial_health=financial_health,
        growth=growth,
        competitive_advantage=competitive_advantage,
        valuation=valuation,
        rd_innovation=rd_innovation,
        risk_profile=risk_profile,
        explanation=explanation,
        disclaimer=disclaimer,
        session=session,
    )


def get_previous_research_runs(
    company_or_ticker: str,
    limit: int = 10,
    session: Optional[Session] = None,
) -> List[ResearchRun]:
    return _repo.get_previous_research_runs(
        company_or_ticker=company_or_ticker,
        limit=limit,
        session=session,
    )


def compare_research_runs(
    current_run_id: str,
    previous_run_id: Optional[str] = None,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    return _repo.compare_research_runs(
        current_run_id=current_run_id,
        previous_run_id=previous_run_id,
        session=session,
    )
