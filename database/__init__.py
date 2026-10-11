"""
Database package for StockResearchAgent
Clean separation between database models, business logic, agents, and tool integrations.
"""

from database.db import (
    Base,
    get_engine,
    get_session_factory,
    get_db_session,
    init_db,
    reset_db,
    DATABASE_URL,
)
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
from database.repository import (
    ResearchRepository,
    create_company,
    get_company,
    create_research_run,
    save_evidence,
    save_metric,
    save_filing,
    save_rd_finding,
    save_score,
    get_previous_research_runs,
    compare_research_runs,
)

__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "get_db_session",
    "init_db",
    "reset_db",
    "DATABASE_URL",
    "Company",
    "ResearchRun",
    "EvidenceItem",
    "FinancialMetric",
    "Filing",
    "NewsArticle",
    "RDProject",
    "ScoreRecord",
    "ResearchRepository",
    "create_company",
    "get_company",
    "create_research_run",
    "save_evidence",
    "save_metric",
    "save_filing",
    "save_rd_finding",
    "save_score",
    "get_previous_research_runs",
    "compare_research_runs",
]
