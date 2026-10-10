"""
SEC EDGAR API Client
Provides read-only access to SEC EDGAR submissions, XBRL company facts, and filings.
Strictly respects SEC access policies, rate limits (<= 10 req/sec), and required User-Agent headers.
"""

import os
import time
import json
import logging
from typing import Optional, Dict, Any, Tuple
import requests

logger = logging.getLogger(__name__)


class SECClient:
    """Read-only client for public SEC EDGAR APIs."""

    BASE_DATA_URL = "https://data.sec.gov"
    BASE_WWW_URL = "https://www.sec.gov"

    def __init__(self, user_agent: Optional[str] = None, timeout: int = 12):
        # SEC requires: User-Agent: Sample Company Name AdminContact@<sample company domain>.com
        self.user_agent = (
            user_agent
            or os.getenv("SEC_EDGAR_USER_AGENT")
            or "StockResearchAgent/1.0 (research@busswizz-finance.local)"
        )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        })
        self._last_request_time = 0.0
        self._min_request_interval = 0.11  # ~9 req/sec to stay safely under 10 req/sec limit
        self._tickers_cache: Optional[Dict[str, Any]] = None

    def check_health(self) -> Dict[str, Any]:
        """Verifies SEC EDGAR accessibility and returns tool status."""
        try:
            # Check ticker lookup endpoint with a 3.0s timeout
            url = f"{self.BASE_WWW_URL}/files/company_tickers.json"
            resp = self._request(url)
            if resp.status_code == 200:
                return {
                    "status": "available",
                    "tool": "sec_edgar",
                    "active_mode": "sec_edgar_direct",
                    "message": "SEC EDGAR public API is healthy (zero API key required).",
                }
            return {
                "status": "degraded",
                "tool": "sec_edgar",
                "active_mode": "sec_edgar_direct",
                "message": f"SEC EDGAR returned status {resp.status_code}.",
            }
        except Exception as e:
            return {
                "status": "unavailable",
                "tool": "sec_edgar",
                "active_mode": "sec_unavailable_fallback",
                "message": f"SEC EDGAR unavailable ({type(e).__name__}). Non-SEC research will continue.",
            }

    def _rate_limit(self) -> None:
        """Enforces SEC rate limit of maximum 10 requests per second."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(
        self,
        url: str,
        retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> requests.Response:
        """Executes HTTP request with rate-limiting, retries on 429/503, and backoff."""
        self._rate_limit()

        # Update Host header dynamically based on domain
        domain = "www.sec.gov" if "www.sec.gov" in url else "data.sec.gov"
        headers = {"Host": domain}

        for attempt in range(retries):
            try:
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", backoff_factor * (2 ** attempt)))
                    time.sleep(min(retry_after, 5.0))
                    continue
                elif response.status_code in (500, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(backoff_factor * (2 ** attempt))
                    continue

                return response
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                if attempt == retries - 1:
                    raise exc
                time.sleep(backoff_factor * (2 ** attempt))

        return self.session.get(url, headers=headers, timeout=self.timeout)

    def load_company_tickers(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Loads the SEC company_tickers.json mapping (caches in memory).
        Maps ~10,000 public companies to CIK, ticker, and company name.
        """
        if self._tickers_cache and not force_refresh:
            return self._tickers_cache

        url = f"{self.BASE_WWW_URL}/files/company_tickers.json"
        response = self._request(url)
        response.raise_for_status()
        self._tickers_cache = response.json()
        return self._tickers_cache

    def get_cik(self, query: str) -> Optional[Tuple[str, str, str]]:
        """
        Resolves a company name or ticker query to (10-digit CIK, official ticker, official name).
        Returns None if no match is found.
        """
        clean_q = query.strip()
        tickers_data = self.load_company_tickers()

        # Pass 1: Exact ticker match
        upper_q = clean_q.upper()
        for item in tickers_data.values():
            if item.get("ticker") == upper_q:
                cik_10 = f"{int(item['cik_str']):010d}"
                return cik_10, item["ticker"], item["title"]

        # Pass 2: Case-insensitive ticker or exact title match
        for item in tickers_data.values():
            ticker = item.get("ticker", "")
            title = item.get("title", "")
            if ticker.lower() == clean_q.lower() or title.lower() == clean_q.lower():
                cik_10 = f"{int(item['cik_str']):010d}"
                return cik_10, ticker, title

        # Pass 3: Title substring match
        clean_q_lower = clean_q.lower()
        for item in tickers_data.values():
            title = item.get("title", "").lower()
            if clean_q_lower in title:
                cik_10 = f"{int(item['cik_str']):010d}"
                return cik_10, item.get("ticker", upper_q), item.get("title", clean_q)

        return None

    def get_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Fetches metadata for all recent filings for a company using its 10-digit CIK.
        Endpoint: https://data.sec.gov/submissions/CIK{cik10}.json
        """
        cik10 = f"{int(cik):010d}"
        url = f"{self.BASE_DATA_URL}/submissions/CIK{cik10}.json"
        try:
            resp = self._request(url)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"SEC submissions returned status {resp.status_code} for CIK {cik10}")
            return None
        except Exception as exc:
            logger.error(f"Error fetching SEC submissions for CIK {cik10}: {exc}")
            return None

    def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Fetches all standardized XBRL disclosures (GAAP and DEI) for a company.
        Endpoint: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json
        """
        cik10 = f"{int(cik):010d}"
        url = f"{self.BASE_DATA_URL}/api/xbrl/companyfacts/CIK{cik10}.json"
        try:
            resp = self._request(url)
            if resp.status_code == 200:
                return resp.json()
            logger.warning(f"SEC companyfacts returned status {resp.status_code} for CIK {cik10}")
            return None
        except Exception as exc:
            logger.error(f"Error fetching SEC companyfacts for CIK {cik10}: {exc}")
            return None

    def get_filing_document(
        self, cik: str, accession_number: str, primary_doc: str
    ) -> Optional[str]:
        """
        Retrieves the raw text/HTML/XML content of a specific SEC filing document.
        """
        url = self.build_document_url(cik, accession_number, primary_doc)
        try:
            resp = self._request(url)
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception as exc:
            logger.error(f"Error fetching filing document {url}: {exc}")
            return None

    def build_document_url(self, cik: str, accession_number: str, primary_doc: str) -> str:
        """
        Builds the canonical public URL for an SEC EDGAR document.
        Example: https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm
        """
        cik_int = int(cik)
        clean_accn = accession_number.replace("-", "")
        # Clean any subpath prefix like xslF345X06/
        doc_name = primary_doc.split("/")[-1]
        return f"{self.BASE_WWW_URL}/Archives/edgar/data/{cik_int}/{clean_accn}/{doc_name}"

    def build_filing_detail_url(self, cik: str, accession_number: str) -> str:
        """Builds URL to the filing index/detail page on SEC EDGAR."""
        cik_int = int(cik)
        clean_accn = accession_number.replace("-", "")
        return f"{self.BASE_WWW_URL}/Archives/edgar/data/{cik_int}/{clean_accn}/{accession_number}-index.htm"
