import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

from src.domain.services.url_builder import normalize_hamrah_base_url

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_host: str = "http://localhost:8000"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://car:car@localhost:5432/car_backend"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    divar_request_delay_ms: int = 300
    divar_max_concurrent_details: int = 10
    divar_extra_headers_json: str = "{}"

    hamrah_mechanic_base_url: str = "https://www.hamrah-mechanic.com"
    hamrah_price_cache_ttl_sec: int = 3600
    hamrah_catalog_cache_ttl_sec: int = 86400

    sms_ir_api_key: str = ""
    sms_ir_line_number: str = ""
    sms_ir_template_id: str = ""
    sms_ir_base_url: str = "https://api.sms.ir/v1"

    default_near_threshold_pct: float = 0.02
    default_max_pages_per_run: int = 5
    crawl_pool_refresh_minutes: int = 30
    purchase_active_days: int = 2
    purchase_ttl_hours: int = 48
    crawl_listings_per_check: int = 10
    shared_pool_listings_limit: int = 150
    shared_pool_max_pages: int = 10
    crawl_result_valid_days: int = 2
    crawl_result_deactivate_days: int = 5
    pricing_cache_ttl_hours: int = 12
    default_pricing_platform: str = "hamrah_mechanic"

    divar_open_api_base_url: str = "https://open-api.divar.ir"
    divar_open_api_key: str = ""

    khodro45_base_url: str = "https://khodro45.com"

    auth_secret_key: str = "change-me-in-production"
    auth_token_max_age_sec: int = 604800
    otp_sandbox: bool = True
    otp_sandbox_code: str = "11111"
    otp_code_length: int = 5
    otp_ttl_sec: int = 300
    cors_origins: str = "*"

    # Secret staff paths: /portal/{uuid1}/{uuid2}/admin|docs|results
    portal_path_uuid_1: str = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    portal_path_uuid_2: str = "b2c3d4e5-f6a7-8901-bcde-f12345678901"

    @field_validator("portal_path_uuid_1", "portal_path_uuid_2")
    @classmethod
    def _validate_portal_uuid(cls, value: str) -> str:
        if not _UUID_RE.match(value.strip()):
            raise ValueError("portal path UUID must be a valid UUID (with hyphens)")
        return value.strip().lower()

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        if "sqlite" not in value or ":///" not in value:
            return value
        prefix, raw_path = value.split(":///", 1)
        if raw_path.startswith("/"):
            return value
        abs_path = (_PROJECT_ROOT / raw_path).resolve()
        return f"{prefix}:////{abs_path.as_posix().lstrip('/')}"

    @field_validator("hamrah_mechanic_base_url")
    @classmethod
    def _normalize_hamrah_base_url(cls, value: str) -> str:
        return normalize_hamrah_base_url(value)

    @property
    def crawl_pool_refresh_sec(self) -> int:
        return self.crawl_pool_refresh_minutes * 60

    @property
    def default_poll_interval_sec(self) -> int:
        """Alias for shared pool refresh interval (seconds)."""
        return self.crawl_pool_refresh_sec

    @property
    def divar_extra_headers(self) -> dict[str, str]:
        try:
            return json.loads(self.divar_extra_headers_json)
        except json.JSONDecodeError:
            return {}


@lru_cache
def get_settings() -> Settings:
    return Settings()
