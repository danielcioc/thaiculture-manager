from pydantic_settings import BaseSettings
from pydantic import SecretStr
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "ThaiCulture Manager API"
    database_url: str
    auth_jwt_secret: Optional[SecretStr] = None
    auth_jwt_issuer: Optional[str] = None
    auth_jwt_audience: Optional[str] = None
    website_integration_enabled: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
