"""Configuration for seo-gsc.

Precedence: explicit function args > environment variables (.env / .env.local) >
YAML config file defaults. Secrets (the service-account key path) only ever come
from the environment, never from the committed YAML.

WHY: pydantic v2 BaseModel (not BaseSettings) so we do not depend on the separate
pydantic-settings package; env overlay is done explicitly and predictably.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

try:  # python-dotenv is a declared dependency; guard anyway for bare environments.
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv missing is non-fatal
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


# OAuth scopes needed for read-only Search Console + GA4 access.
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


class PropertyConfig(BaseModel):
    """One verified site to analyze."""

    name: str
    # GSC property identifier: either a URL prefix ("https://example.com/")
    # or a domain property ("sc-domain:example.com").
    site_url: str
    ga4_property_id: str | None = None
    default_country: str | None = None  # ISO-3 (for example "are", "usa"); None = all
    notes: str | None = None


class Thresholds(BaseModel):
    """Tunable cut-offs for the five analysis modes."""

    quick_win_min_position: float = 5.0
    quick_win_max_position: float = 15.0
    quick_win_min_impressions: int = 200

    # Flag a title/meta CTR issue when actual CTR is below this fraction of the
    # CTR expected at the page's position (0.7 = 30 percent under-performance).
    low_ctr_factor: float = 0.7
    low_ctr_min_impressions: int = 100

    # A content gap: impressions above this, clicks at or below this, no page.
    gap_min_impressions: int = 50
    gap_max_clicks: int = 1

    cluster_min_queries: int = 2
    cluster_min_shared_tokens: int = 1


class SeoConfig(BaseModel):
    """Top-level toolkit configuration."""

    properties: dict[str, PropertyConfig] = Field(default_factory=dict)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    # Optional per-deployment CTR curve override (position -> expected CTR).
    ctr_curve: dict[int, float] | None = None

    # Resolved from the environment, not the YAML.
    service_account_file: str | None = None
    oauth_token_file: str | None = None

    def property(self, key: str) -> PropertyConfig:
        if key in self.properties:
            return self.properties[key]
        # Allow lookup by site display name too.
        for prop in self.properties.values():
            if prop.name == key or prop.site_url == key:
                return prop
        raise KeyError(
            f"Unknown property '{key}'. Known: {', '.join(self.properties) or '(none configured)'}"
        )


def load_config(path: str | Path | None = None, env_file: str | Path | None = None) -> SeoConfig:
    """Load YAML config, then overlay environment / .env secrets."""
    # Load .env / .env.local so secrets land in os.environ.
    if env_file:
        load_dotenv(env_file)
    else:
        for candidate in (".env.local", ".env"):
            p = Path(candidate)
            if p.exists():
                load_dotenv(p)

    data: dict = {}
    if path:
        cfg_path = Path(path)
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    config = SeoConfig.model_validate(data)

    # Secrets strictly from the environment.
    config.service_account_file = os.environ.get("SEO_GSC_SERVICE_ACCOUNT_FILE") or config.service_account_file
    config.oauth_token_file = os.environ.get("SEO_GSC_OAUTH_TOKEN_FILE") or config.oauth_token_file
    return config
