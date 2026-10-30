from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IITA @60 Comment Moderation API"
    database_url: str = "sqlite:///./iita_at60.db"
    secret_key: str = "development-only-change-this-secret"
    admin_username: str = "admin"
    admin_password: str = "ChangeThisAdminPassword123!"
    cors_origins: str = "http://localhost:3000"
    sentiment_model: str = "distilbert-base-uncased-finetuned-sst-2-english"
    sentiment_neutral_band: float = 0.15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
