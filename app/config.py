"""Runtime configuration, loaded from the environment.

Defaults are deliberately safe: with no configuration at all the service boots
in DRY_RUN mode and never sends a single real request. You opt into hitting real
upstreams by setting STORM_TARGET_BASE_URL and DRY_RUN=false.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings for the service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # HTTP server
    http_host: str = Field(default="0.0.0.0", alias="HTTP_HOST")
    http_port: int = Field(default=8080, alias="HTTP_PORT")

    # Safety: when true, scenarios simulate load locally and send NO real
    # traffic. This is the default so a fresh checkout is harmless.
    dry_run: bool = Field(default=True, alias="DRY_RUN")

    # Where simulated traffic is sent when dry_run is false. Empty forces
    # dry-run behaviour regardless of the flag.
    storm_target_base_url: str = Field(default="", alias="STORM_TARGET_BASE_URL")

    # Storm sizing
    default_storm_size: int = Field(default=5000, alias="DEFAULT_STORM_SIZE")
    max_storm_size: int = Field(default=20000, alias="MAX_STORM_SIZE")
    concurrency: int = Field(default=100, alias="CONCURRENCY")
    request_timeout_seconds: float = Field(default=10.0, alias="REQUEST_TIMEOUT_SECONDS")

    # Per-scenario upstream endpoints (optional). When unset they fall back to
    # STORM_TARGET_BASE_URL + a conventional path.
    dnb_url: str = Field(default="", alias="DNB_URL")
    valitive_url: str = Field(default="", alias="VALITIVE_URL")
    creditsafe_url: str = Field(default="", alias="CREDITSAFE_URL")
    crm_url: str = Field(default="", alias="CRM_URL")
    alarm_gateway_url: str = Field(default="", alias="ALARM_GATEWAY_URL")

    # Deterministic synthetic data when set (>= 0); -1 leaves Faker unseeded.
    faker_seed: int = Field(default=-1, alias="FAKER_SEED")

    # Observability
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")

    @property
    def effectively_dry_run(self) -> bool:
        """Dry-run is forced when no target is configured, whatever DRY_RUN says."""
        return self.dry_run or not self.storm_target_base_url

    def endpoint(self, override: str, default_path: str) -> str:
        """Resolve a scenario endpoint from its override or the shared target base."""
        if override:
            return override
        if not self.storm_target_base_url:
            return ""
        return self.storm_target_base_url.rstrip("/") + default_path


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
