"""
SQLite Database Layer
Stores research sessions, fundamental financial metrics, SEC facts, and web search sources.
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import contextmanager


class Database:
    """Thread-safe SQLite storage for stock research sessions and extracted data."""

    def __init__(self, db_path: str = "data/research.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables if they do not exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS research_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    company TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    model_used TEXT,
                    full_report TEXT,
                    raw_data_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS financial_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    current_price REAL,
                    market_cap REAL,
                    revenue REAL,
                    net_income REAL,
                    eps REAL,
                    pe_ratio REAL,
                    ps_ratio REAL,
                    ev_ebitda REAL,
                    gross_margin REAL,
                    operating_margin REAL,
                    free_cash_flow REAL,
                    cash REAL,
                    debt REAL,
                    revenue_growth REAL,
                    eps_growth REAL,
                    data_source TEXT,
                    FOREIGN KEY (session_id) REFERENCES research_sessions (session_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sec_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    value TEXT,
                    filing_type TEXT,
                    filing_date TEXT,
                    accession_number TEXT,
                    source_url TEXT,
                    snippet TEXT,
                    FOREIGN KEY (session_id) REFERENCES research_sessions (session_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS web_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    snippet TEXT,
                    engine TEXT,
                    FOREIGN KEY (session_id) REFERENCES research_sessions (session_id)
                )
            """)
            conn.commit()

    def check_health(self) -> Dict[str, Any]:
        """Verifies database connectivity."""
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return {"status": "healthy", "path": self.db_path}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def save_session(
        self,
        session_id: str,
        company: str,
        ticker: str,
        status: str,
        model_used: str,
        full_report: str,
        financial_metrics: Optional[Dict[str, Any]] = None,
        sec_facts: Optional[List[Dict[str, Any]]] = None,
        web_sources: Optional[List[Dict[str, Any]]] = None,
        raw_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persists a complete research session and its associated data points."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO research_sessions
                (session_id, company, ticker, status, model_used, full_report, raw_data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    company,
                    ticker,
                    status,
                    model_used,
                    full_report,
                    json.dumps(raw_data or {}),
                ),
            )

            # Save Financial Snapshot if available
            if financial_metrics:
                conn.execute(
                    """
                    INSERT INTO financial_snapshots (
                        session_id, ticker, current_price, market_cap, revenue, net_income,
                        eps, pe_ratio, ps_ratio, ev_ebitda, gross_margin, operating_margin,
                        free_cash_flow, cash, debt, revenue_growth, eps_growth, data_source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        ticker,
                        financial_metrics.get("current_price"),
                        financial_metrics.get("market_cap"),
                        financial_metrics.get("revenue"),
                        financial_metrics.get("net_income"),
                        financial_metrics.get("eps"),
                        financial_metrics.get("pe_ratio"),
                        financial_metrics.get("ps_ratio"),
                        financial_metrics.get("ev_ebitda"),
                        financial_metrics.get("gross_margin"),
                        financial_metrics.get("operating_margin"),
                        financial_metrics.get("free_cash_flow"),
                        financial_metrics.get("cash"),
                        financial_metrics.get("debt"),
                        financial_metrics.get("revenue_growth"),
                        financial_metrics.get("eps_growth"),
                        financial_metrics.get("data_source", "yfinance"),
                    ),
                )

            # Save SEC Facts
            if sec_facts:
                for f in sec_facts:
                    conn.execute(
                        """
                        INSERT INTO sec_facts
                        (session_id, ticker, claim, value, filing_type, filing_date, accession_number, source_url, snippet)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            ticker,
                            f.get("claim", ""),
                            f.get("value"),
                            f.get("filing_type", ""),
                            f.get("filing_date", ""),
                            f.get("accession_number", ""),
                            f.get("source_url", ""),
                            f.get("source_snippet") or f.get("snippet", ""),
                        ),
                    )

            # Save Web Sources
            if web_sources:
                for w in web_sources:
                    conn.execute(
                        """
                        INSERT INTO web_sources (session_id, title, url, snippet, engine)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            session_id,
                            w.get("title", ""),
                            w.get("url", ""),
                            w.get("snippet", ""),
                            w.get("engine", "web"),
                        ),
                    )

            conn.commit()

    def get_recent_sessions(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recent research sessions."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT session_id, company, ticker, created_at, status, model_used
                FROM research_sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full details for a session."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM research_sessions WHERE session_id = ?", (session_id,))
            session = cur.fetchone()
            if not session:
                return None

            result = dict(session)

            # Fetch financials
            cur.execute("SELECT * FROM financial_snapshots WHERE session_id = ?", (session_id,))
            fin = cur.fetchone()
            result["financial_snapshot"] = dict(fin) if fin else None

            # Fetch SEC facts
            cur.execute("SELECT * FROM sec_facts WHERE session_id = ?", (session_id,))
            result["sec_facts"] = [dict(r) for r in cur.fetchall()]

            # Fetch Web sources
            cur.execute("SELECT * FROM web_sources WHERE session_id = ?", (session_id,))
            result["web_sources"] = [dict(r) for r in cur.fetchall()]

            return result
