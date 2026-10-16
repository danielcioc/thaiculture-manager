from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from typing import Optional


DEFAULT_LOCAL_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"


def parse_cors_origins(value: str) -> list[str]:
    origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
    if any("*" in origin for origin in origins):
        raise ValueError("CORS_ALLOWED_ORIGINS must list explicit origins; wildcard is not allowed")
    return origins


class Settings(BaseSettings):
    app_name: str = "ThaiCulture Manager API"
    database_url: str
    auth_jwt_secret: Optional[SecretStr] = None
    auth_jwt_issuer: Optional[str] = None
    auth_jwt_audience: Optional[str] = None
    website_integration_enabled: bool = False
    cors_allowed_origins: str = DEFAULT_LOCAL_CORS_ORIGINS
    website_max_body_bytes: int = Field(default=16384, ge=1024, le=1048576)
    website_catalog_requests_per_minute: int = Field(default=60, ge=1, le=10000)
    website_pricing_requests_per_minute: int = Field(default=20, ge=1, le=10000)
    website_bookings_requests_per_minute: int = Field(default=5, ge=1, le=10000)
    website_db_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    website_db_statement_timeout_ms: int = Field(default=5000, ge=100, le=120000)

    class Config:
        env_file = ".env"


settings = Settings()
