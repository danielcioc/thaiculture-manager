from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "ThaiCulture Manager API"
    database_url: str = "postgresql://tct_admin:tct_local_password@postgres:5432/thaiculture_manager"

    class Config:
        env_file = ".env"


settings = Settings()
