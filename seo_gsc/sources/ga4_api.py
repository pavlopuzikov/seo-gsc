"""Live GA4 engagement pull via the Analytics Data REST API.

Secondary source: enriches the weekly report with on-page engagement
(sessions, engaged sessions, conversions) per landing page, so we can tell a
"high clicks but bouncing" page from a "high clicks and converting" one.

Built on httpx + google-auth. Endpoint:
POST https://analyticsdata.googleapis.com/v1beta/properties/{id}:runReport
Scope: https://www.googleapis.com/auth/analytics.readonly
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd

from ..config import GA4_SCOPE
from .gsc_api import _access_token

_REPORT_URL = "https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport"


class GA4Client:
    """Thin GA4 Data API client returning a tidy enrichment DataFrame."""

    def __init__(
        self,
        service_account_file: str | None = None,
        oauth_token_file: str | None = None,
        scope: str = GA4_SCOPE,
        timeout: float = 60.0,
    ) -> None:
        self.service_account_file = service_account_file
        self.oauth_token_file = oauth_token_file
        self.scope = scope
        self.timeout = timeout

    def run_report(
        self,
        property_id: str,
        start_date: str,
        end_date: str,
        dimensions: Sequence[str] = ("landingPagePlusQueryString",),
        metrics: Sequence[str] = ("sessions", "engagedSessions", "conversions"),
    ) -> pd.DataFrame:
        """Return one row per dimension tuple with the requested metrics."""
        import httpx

        token = _access_token(self.service_account_file, self.oauth_token_file, [self.scope])
        url = _REPORT_URL.format(pid=property_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": 100000,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError(
                f"GA4 API error {resp.status_code} for property {property_id}: {resp.text[:300]}"
            )

        payload = resp.json()
        out: list[dict] = []
        for row in payload.get("rows", []):
            record: dict = {}
            for dim_def, cell in zip(dimensions, row.get("dimensionValues", [])):
                record[dim_def] = cell.get("value", "")
            for met_def, cell in zip(metrics, row.get("metricValues", [])):
                try:
                    record[met_def] = float(cell.get("value", 0) or 0)
                except (TypeError, ValueError):
                    record[met_def] = 0.0
            out.append(record)
        return pd.DataFrame(out)
