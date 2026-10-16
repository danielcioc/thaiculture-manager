from pydantic_settings import BaseSettings
from pydantic import SecretStr
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

    class Config:
        env_file = ".env"


settings = Settings()
