"""Live Google Search Console pull via the Search Analytics REST API.

Built on httpx + google-auth (both in shared/venv311) rather than
google-api-python-client, so no extra install is required. Service-account auth
is the default (unattended weekly run); an authorized-user OAuth token file is
also supported.

Endpoint: POST https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query
Docs scope: https://www.googleapis.com/auth/webmasters.readonly
"""

from __future__ import annotations

import urllib.parse
from typing import Sequence

from ..config import GSC_SCOPE
from ..models import SearchDataset

_QUERY_URL = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
_PAGE_SIZE = 25000  # GSC maximum rows per request


def _access_token(service_account_file: str | None, oauth_token_file: str | None, scopes: Sequence[str]) -> str:
    """Mint a bearer token from a service account or an OAuth token file."""
    # Imported lazily so the package imports without google-auth present.
    from google.auth.transport.requests import Request

    if service_account_file:
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=list(scopes)
        )
    elif oauth_token_file:
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(oauth_token_file, scopes=list(scopes))
    else:
        raise ValueError(
            "No Google credentials configured. Set SEO_GSC_SERVICE_ACCOUNT_FILE "
            "(preferred) or SEO_GSC_OAUTH_TOKEN_FILE in .env.local."
        )

    try:
        creds.refresh(Request())
    except Exception as exc:  # re-raised with context; covers expired/missing refresh tokens
        raise RuntimeError(f"Failed to refresh Google credentials: {exc}") from exc
    if not creds.token:
        raise RuntimeError("Failed to obtain an access token from the provided credentials.")
    return creds.token


class GSCClient:
    """Thin Search Console Search Analytics client."""

    def __init__(
        self,
        service_account_file: str | None = None,
        oauth_token_file: str | None = None,
        scope: str = GSC_SCOPE,
        timeout: float = 60.0,
    ) -> None:
        self.service_account_file = service_account_file
        self.oauth_token_file = oauth_token_file
        self.scope = scope
        self.timeout = timeout

    def query(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Sequence[str] = ("query", "page"),
        country: str | None = None,
        label: str = "",
    ) -> SearchDataset:
        """Pull rows for a date range, paging through all results.

        dimensions: any of query, page, country, device, date (GSC names).
        country: optional ISO-3 filter (for example "are").
        Returns a SearchDataset with one row per dimension tuple.
        """
        import httpx

        token = _access_token(self.service_account_file, self.oauth_token_file, [self.scope])
        url = _QUERY_URL.format(site=urllib.parse.quote(site_url, safe=""))
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        dim_filters = []
        if country:
            dim_filters.append(
                {"filters": [{"dimension": "country", "operator": "equals", "expression": country}]}
            )

        rows: list[dict] = []
        start_row = 0
        with httpx.Client(timeout=self.timeout) as client:
            while True:
                body = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": list(dimensions),
                    "rowLimit": _PAGE_SIZE,
                    "startRow": start_row,
                    "dataState": "final",
                }
                if dim_filters:
                    body["dimensionFilterGroups"] = dim_filters

                resp = client.post(url, headers=headers, json=body)
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"GSC API error {resp.status_code} for {site_url}: {resp.text[:300]}"
                    )
                page_rows = resp.json().get("rows", [])
                if not page_rows:
                    break
                rows.extend(page_rows)
                if len(page_rows) < _PAGE_SIZE:
                    break
                start_row += _PAGE_SIZE

        return self._rows_to_dataset(rows, dimensions, label or f"gsc:{site_url}")

    @staticmethod
    def _rows_to_dataset(api_rows: list[dict], dimensions: Sequence[str], label: str) -> SearchDataset:
        out: list[dict] = []
        for r in api_rows:
            keys = r.get("keys", [])
            record = {
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0.0),
                "position": r.get("position", 0.0),
            }
            for dim, value in zip(dimensions, keys):
                # GSC dimension names map directly to our canonical columns.
                record[dim] = value
            out.append(record)
        return SearchDataset.from_rows(out, label=label)
