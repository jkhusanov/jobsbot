from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str = Field(..., min_length=10)
    jobs_api_url: str = Field(..., min_length=1)

    @field_validator("jobs_api_url")
    @classmethod
    def _require_http_scheme(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("JOBS_API_URL must start with http:// or https://")
        return v

    @field_validator("bot_token")
    @classmethod
    def _bot_token_shape(cls, v: str) -> str:
        # Telegram bot tokens look like <int>:<35+ alnum/_-> chars.
        # Catches obvious copy-paste mistakes (extra whitespace, the word
        # "Bearer", placeholder text) before the bot tries to authenticate.
        import re
        if not re.fullmatch(r"\d{6,12}:[A-Za-z0-9_-]{30,}", v.strip()):
            raise ValueError("BOT_TOKEN does not look like a valid Telegram bot token")
        return v.strip()
    jobs_api_auth_header: str | None = None
    jobs_api_timeout_seconds: int = 10
    jobs_cache_ttl_seconds: int = 60

    admin_chat_id: int = 0
    admin_username: str | None = None

    database_path: Path = Path("./bot.db")
    max_cv_size_mb: int = 20
    log_level: str = "INFO"

    @property
    def max_cv_size_bytes(self) -> int:
        return self.max_cv_size_mb * 1024 * 1024


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
