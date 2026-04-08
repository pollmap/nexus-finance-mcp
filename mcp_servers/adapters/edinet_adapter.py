"""
EDINET Adapter — Japanese corporate disclosure system (金融庁 EDINET).
Japanese equivalent of DART (Korea) / EDGAR (US).
API v2: https://api.edinet-fsa.go.jp/api/v2/
"""
import logging
import os
import sys
from pathlib import Path
import requests
from utils.http_client import get_session
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_servers.core.rate_limiter import get_limiter
from mcp_servers.core.responses import error_response, success_response

logger = logging.getLogger(__name__)
_session = get_session("edinet_adapter")

BASE_URL = "https://api.edinet-fsa.go.jp/api/v2"


class EDINETAdapter:
    """EDINET API v2 — Japanese corporate filings and financial data."""

    def __init__(self):
        self._api_key = os.getenv("EDINET_API_KEY", "")
        self._limiter = get_limiter()
        if not self._api_key:
            logger.warning("EDINET_API_KEY not set")

    def _rate_limit(self):
        self._limiter.acquire("edinet")

    def search_filings(self, date: str = None, filing_type: str = "2") -> Dict[str, Any]:
        """
        Search EDINET filings by date.

        Args:
            date: Filing date (YYYY-MM-DD, default: today)
            filing_type: 1=metadata only, 2=with filing details
        """
        try:
            self._rate_limit()
            if not date:
                from datetime import datetime
                date = datetime.now().strftime("%Y-%m-%d")

            url = f"{BASE_URL}/documents.json"
            params = {"date": date, "type": filing_type, "Subscription-Key": self._api_key}
            resp = _session.get(url, params=params, timeout=15)
            data = (resp.json() if resp.status_code == 200 else {})

            results = data.get("results", [])
            records = []
            for r in results:
                # Filter out empty/null entries
                if not r.get("edinetCode"):
                    continue
                records.append({
                    "edinet_code": r.get("edinetCode", ""),
                    "company": r.get("filerName", ""),
                    "doc_type": r.get("docTypeCode", ""),
                    "doc_type_name": r.get("docDescription", ""),
                    "filing_date": r.get("submitDateTime", ""),
                    "doc_id": r.get("docID", ""),
                    "period": (r.get("periodStart") or "") + "~" + (r.get("periodEnd") or ""),
                    "security_code": r.get("secCode", ""),
                })

            return success_response(records, source="EDINET", date=date)
        except Exception as e:
            logger.error(f"EDINET search error: {e}")
            return error_response(f"EDINET filing search failed: {e}")

    def get_company_filings(self, edinet_code: str, filing_type: str = "2") -> Dict[str, Any]:
        """
        Get recent filings for a specific company.

        Args:
            edinet_code: EDINET company code (e.g., E02529 for Toyota)
        """
        try:
            self._rate_limit()
            # Search last 30 days
            from datetime import datetime, timedelta
            records = []
            for i in range(30):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                url = f"{BASE_URL}/documents.json"
                params = {"date": date, "type": filing_type, "Subscription-Key": self._api_key}
                resp = _session.get(url, params=params, timeout=10)
                data = (resp.json() if resp.status_code == 200 else {})

                for r in data.get("results", []):
                    if r.get("edinetCode") == edinet_code:
                        records.append({
                            "doc_id": r.get("docID", ""),
                            "doc_type": r.get("docDescription", ""),
                            "filing_date": r.get("submitDateTime", ""),
                            "period": (r.get("periodStart") or "") + "~" + (r.get("periodEnd") or ""),
                        })

                if len(records) >= 5:
                    break

            return success_response(records, source="EDINET", edinet_code=edinet_code)
        except Exception as e:
            logger.error(f"EDINET company filings error: {e}")
            return error_response(f"EDINET company filing search failed: {e}")

    def get_document_info(self, doc_id: str) -> Dict[str, Any]:
        """
        Get document metadata by document ID.

        Args:
            doc_id: EDINET document ID (e.g., S100XXXX)
        """
        try:
            self._rate_limit()
            url = f"{BASE_URL}/documents/{doc_id}"
            params = {"type": 1, "Subscription-Key": self._api_key}
            resp = _session.get(url, params=params, timeout=15)

            if resp.status_code == 200:
                # Type 1 returns metadata JSON
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    data = resp.json()
                    return success_response(data, source="EDINET", doc_id=doc_id)
                else:
                    return success_response(None, source="EDINET", doc_id=doc_id,
                                            message="Document available for download (XBRL/PDF)",
                                            size_bytes=len(resp.content))
            return error_response(f"HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"EDINET document error: {e}")
            return error_response(f"EDINET document retrieval failed: {e}")

    def search_by_security_code(self, security_code: str) -> Dict[str, Any]:
        """
        Search EDINET code by Japanese security code (証券コード).

        Args:
            security_code: 4-digit security code (e.g., 7203 for Toyota)
        """
        try:
            self._rate_limit()
            # EDINET code list API
            url = f"{BASE_URL}/edinetcode.json"
            params = {"Subscription-Key": self._api_key}
            resp = _session.get(url, params=params, timeout=15)
            data = (resp.json() if resp.status_code == 200 else {})

            results = data.get("results", [])
            matches = [r for r in results if str(r.get("secCode", "")).startswith(str(security_code))]

            records = []
            for r in matches:
                records.append({
                    "edinet_code": r.get("edinetCode", ""),
                    "company": r.get("filerName", ""),
                    "security_code": r.get("secCode", ""),
                    "industry": r.get("industryCode", ""),
                })

            return success_response(records, source="EDINET", security_code=security_code)
        except Exception as e:
            logger.error(f"EDINET search error: {e}")
            return error_response(f"EDINET code search failed: {e}")
