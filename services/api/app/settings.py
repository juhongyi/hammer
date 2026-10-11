from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent.parent / ".env.local",
        extra="ignore",
    )
    database_url: str = "postgresql+psycopg://poc:local-poc-password@localhost:5432/presentation"
    cloudflare_account_id: str = ""
    cloudflare_api_token: SecretStr = SecretStr("")
    cloudflare_ai_model: str = "@cf/ibm-granite/granite-4.0-h-micro"
    typesafe_api_key: SecretStr = SecretStr("")
    typesafe_model: str = "jev-1.13.0"
    model_timeout_seconds: float = 120
