"""Configuration management for Telegram Bet Bot."""

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

VALID_ENVIRONMENTS = {"development", "testing", "production"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigurationError(Exception):
    """Raised when application configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    """Application configuration container."""

    app_env: str = "development"
    log_level: str = "INFO"
    bot_token: str | None = None

    @classmethod
    def from_env(cls, env_path: Path | str | None = None) -> "Config":
        """Load and validate configuration from environment variables and .env file."""
        if env_path is not None:
            load_dotenv(dotenv_path=env_path)
        else:
            load_dotenv()

        raw_env = os.getenv("APP_ENV", "development").strip().lower()
        if raw_env not in VALID_ENVIRONMENTS:
            raise ConfigurationError(
                f"Invalid APP_ENV '{raw_env}'. Must be one of: {sorted(VALID_ENVIRONMENTS)}"
            )

        raw_log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        if raw_log_level not in VALID_LOG_LEVELS:
            raise ConfigurationError(
                f"Invalid LOG_LEVEL '{raw_log_level}'. Must be one of: {sorted(VALID_LOG_LEVELS)}"
            )

        bot_token = os.getenv("BOT_TOKEN")
        if bot_token:
            bot_token = bot_token.strip()

        if raw_env == "production" and not bot_token:
            raise ConfigurationError(
                "BOT_TOKEN environment variable is required when APP_ENV is 'production'."
            )

        return cls(
            app_env=raw_env,
            log_level=raw_log_level,
            bot_token=bot_token,
        )
