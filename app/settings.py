from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    app_env: str = "dev"
    secret_key: str
    fernet_key: str
    deepseek_api_key: str

    database_url: str = "sqlite:///./app.db"

    imap_host: str = "imap.163.com"
    imap_port: int = 993
    smtp_host: str = "smtp.163.com"
    smtp_port: int = 465

    poll_interval_seconds: int = 600
    fetch_limit: int = 20
    summary_max_chars: int = 2000

    log_level: str = "INFO"

    @field_validator("secret_key", "fernet_key", "deepseek_api_key")
    def not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("value required")
        return v

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    return Settings()