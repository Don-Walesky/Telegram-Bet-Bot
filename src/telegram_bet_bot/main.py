"""Application entry point for Telegram Bet Bot."""

import logging
import sys
from telegram_bet_bot.config import Config, ConfigurationError


def setup_logging(log_level: str) -> None:
    """Configure basic logger with standard format."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> int:
    """Execute the application foundation startup sequence."""
    try:
        config = Config.from_env()
    except ConfigurationError as err:
        print(f"Configuration error: {err}", file=sys.stderr)
        return 1

    setup_logging(config.log_level)
    logger = logging.getLogger("telegram_bet_bot")
    logger.info("Telegram Bet Bot foundation initialized successfully [env=%s]", config.app_env)
    return 0


if __name__ == "__main__":
    sys.exit(main())
