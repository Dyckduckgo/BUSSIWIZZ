"""
SQLAlchemy Database Models for StockResearchAgent
Defines persistent schema for:
- companies: Tracked public equities
- research_runs: Execution lifecycle and metadata for each research run
- evidence: Audited evidence items with 7-point verifier tracking
- financial_metrics: Quantitative snapshots and ratios
- filings: Regulatory SEC submissions and XBRL extractions
- news: Real-time web news and articles
- rd_projects: R&D spending, technological pipelines, and discoveries
- scores: 7-dimension explainable research scores and audit explanations
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from database.db import Base


class Company(Base):
    """Registered company entity under analysis."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    cik = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    research_runs = relationship("ResearchRun", back_populates="company", cascade="all, delete-orphan", order_by="desc(ResearchRun.start_time)")
    evidence = relationship("EvidenceItem", back_populates="company", cascade="all, delete-orphan")
    financial_metrics = relationship("FinancialMetric", back_populates="company", cascade="all, delete-orphan")
    filings = relationship("Filing", back_populates="company", cascade="all, delete-orphan")
    news = relationship("NewsArticle", back_populates="company", cascade="all, delete-orphan")
    rd_projects = relationship("RDProject", back_populates="company", cascade="all, delete-orphan")
    scores = relationship("ScoreRecord", back_populates="company", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "name": self.name,
            "sector": self.sector,
            "industry": self.industry,
            "cik": self.cik,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ResearchRun(Base):
    """
    An individual multi-agent research execution.
    Attributes: run ID, company, start time, completion time, final score, report path.
    """
    __tablename__ = "research_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    company_ticker = Column(String(20), nullable=False, index=True)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    completion_time = Column(DateTime, nullable=True)
    final_score = Column(Float, nullable=True)
    report_path = Column(Text, nullable=True)
    status = Column(String(50), default="COMPLETED", nullable=False)  # COMPLETED, IN_PROGRESS, FAILED
    model_used = Column(String(100), default="multi_agent_pipeline", nullable=True)

    # Relationships
    company = relationship("Company", back_populates="research_runs")
    evidence = relationship("EvidenceItem", back_populates="research_run", cascade="all, delete-orphan")
    financial_metrics = relationship("FinancialMetric", back_populates="research_run", cascade="all, delete-orphan")
    filings = relationship("Filing", back_populates="research_run", cascade="all, delete-orphan")
    news = relationship("NewsArticle", back_populates="research_run", cascade="all, delete-orphan")
    rd_projects = relationship("RDProject", back_populates="research_run", cascade="all, delete-orphan")
    scores = relationship("ScoreRecord", back_populates="research_run", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "company_id": self.company_id,
            "company_ticker": self.company_ticker,
            "company_name": self.company.name if self.company else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "completion_time": self.completion_time.isoformat() if self.completion_time else None,
            "final_score": self.final_score,
            "report_path": self.report_path,
            "status": self.status,
            "model_used": self.model_used,
        }


class EvidenceItem(Base):
    """
    Persistent record of an evidence item gathered by an agent and audited by the verifier.
    Retains: claim, source URL, source date, source type, agent, confidence,
    verified status, verification reason, timestamp.
    """
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    claim = Column(Text, nullable=False)
    source_url = Column(Text, default="")
    source_name = Column(String(255), default="")
    source_date = Column(String(100), default="")
    source_type = Column(String(50), default="NEWS")  # SEC_FILING, FINANCIAL_API, ACADEMIC_PAPER, NEWS, OFFICIAL_PR
    agent = Column(String(100), nullable=False)  # WebAgent, FinancialAgent, SECAgent, RDAgent
    confidence = Column(Float, default=0.8)
    verified_status = Column(Boolean, default=True, nullable=False, index=True)
    verification_reason = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    epistemic_status = Column(String(50), default="FACT")  # FACT, INFERENCE, SPECULATION
    category = Column(String(100), default="")  # e.g., risks, catalysts, growth, new_products
    numerical_value = Column(Float, nullable=True)
    metric_name = Column(String(100), nullable=True)

    # Relationships
    research_run = relationship("ResearchRun", back_populates="evidence")
    company = relationship("Company", back_populates="evidence")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "claim": self.claim,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "source_date": self.source_date,
            "source_type": self.source_type,
            "agent": self.agent,
            "confidence": self.confidence,
            "verified_status": self.verified_status,
            "verification_reason": self.verification_reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "epistemic_status": self.epistemic_status,
            "category": self.category,
            "numerical_value": self.numerical_value,
            "metric_name": self.metric_name,
        }


class FinancialMetric(Base):
    """Quantitative metric snapshot for a company during a research run."""
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=True)
    metric_text = Column(String(100), nullable=True)
    period = Column(String(50), default="TTM")
    data_source = Column(String(100), default="yfinance")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    research_run = relationship("ResearchRun", back_populates="financial_metrics")
    company = relationship("Company", back_populates="financial_metrics")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_text": self.metric_text,
            "period": self.period,
            "data_source": self.data_source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class Filing(Base):
    """Regulatory filing submission and disclosure from the SEC."""
    __tablename__ = "filings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    form_type = Column(String(50), nullable=False)
    filing_date = Column(String(50), default="")
    accession_number = Column(String(100), default="")
    source_url = Column(Text, default="")
    description = Column(Text, default="")
    facts_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    research_run = relationship("ResearchRun", back_populates="filings")
    company = relationship("Company", back_populates="filings")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "form_type": self.form_type,
            "filing_date": self.filing_date,
            "accession_number": self.accession_number,
            "source_url": self.source_url,
            "description": self.description,
            "facts_count": self.facts_count,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class NewsArticle(Base):
    """Real-time news item retrieved during web research."""
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, default="")
    publisher = Column(String(255), default="")
    published_date = Column(String(100), default="")
    snippet = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    research_run = relationship("ResearchRun", back_populates="news")
    company = relationship("Company", back_populates="news")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "published_date": self.published_date,
            "snippet": self.snippet,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class RDProject(Base):
    """R&D project, patent, technical paper, or technology pipeline discovery."""
    __tablename__ = "rd_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(Text, nullable=False)
    category = Column(String(100), default="New products")
    description = Column(Text, default="")
    maturity = Column(String(100), default="")
    potential_impact = Column(Text, default="")
    source_url = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    research_run = relationship("ResearchRun", back_populates="rd_projects")
    company = relationship("Company", back_populates="rd_projects")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "maturity": self.maturity,
            "potential_impact": self.potential_impact,
            "source_url": self.source_url,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class ScoreRecord(Base):
    """Explainable institutional research score across the 7 dimensions."""
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("research_runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True, index=True)
    total_score = Column(Float, nullable=False)
    business_quality = Column(Float, default=0.0)
    financial_health = Column(Float, default=0.0)
    growth = Column(Float, default=0.0)
    competitive_advantage = Column(Float, default=0.0)
    valuation = Column(Float, default=0.0)
    rd_innovation = Column(Float, default=0.0)
    risk_profile = Column(Float, default=0.0)
    explanation = Column(Text, default="")
    disclaimer = Column(Text, default="")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    research_run = relationship("ResearchRun", back_populates="scores")
    company = relationship("Company", back_populates="scores")

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "total_score": self.total_score,
            "business_quality": self.business_quality,
            "financial_health": self.financial_health,
            "growth": self.growth,
            "competitive_advantage": self.competitive_advantage,
            "valuation": self.valuation,
            "rd_innovation": self.rd_innovation,
            "risk_profile": self.risk_profile,
            "explanation": self.explanation,
            "disclaimer": self.disclaimer,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
