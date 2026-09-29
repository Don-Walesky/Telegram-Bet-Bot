"""Smoke tests for Telegram Bet Bot foundation."""

import importlib
from pathlib import Path
import pytest
from telegram_bet_bot.config import Config, ConfigurationError
from telegram_bet_bot.main import main


def test_package_imports_successfully() -> None:
    """Verify that the package imports and exposes a version string."""
    pkg = importlib.import_module("telegram_bet_bot")
    assert pkg is not None
    assert hasattr(pkg, "__version__")
    assert isinstance(pkg.__version__, str)


def test_application_entry_point_importable() -> None:
    """Verify that the main application entry point is importable and callable."""
    assert callable(main)


def test_config_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify default configuration loads safely without requiring any secrets."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    cfg = Config.from_env(load_dotenv_file=False)
    assert cfg.app_env == "development"
    assert cfg.log_level == "INFO"
    assert cfg.bot_token is None


def test_config_invalid_environment_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify invalid environment raises a clear ConfigurationError."""
    monkeypatch.setenv("APP_ENV", "unsupported_env")
    with pytest.raises(ConfigurationError, match="Invalid APP_ENV"):
        Config.from_env(load_dotenv_file=False)


def test_config_invalid_log_level_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify invalid log level raises a clear ConfigurationError."""
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE_UNKNOWN")
    with pytest.raises(ConfigurationError, match="Invalid LOG_LEVEL"):
        Config.from_env(load_dotenv_file=False)


def test_config_production_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify production environment requires BOT_TOKEN."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(ConfigurationError, match="BOT_TOKEN environment variable is required"):
        Config.from_env(load_dotenv_file=False)


def test_config_from_explicit_env_file(tmp_path: Path) -> None:
    """Verify loading configuration from an explicit custom .env file."""
    env_file = tmp_path / "custom.env"
    env_file.write_text("APP_ENV=testing\nLOG_LEVEL=DEBUG\nBOT_TOKEN=test-token\n")
    cfg = Config.from_env(env_path=env_file)
    assert cfg.app_env == "testing"
    assert cfg.log_level == "DEBUG"
    assert cfg.bot_token == "test-token"


def test_main_execution_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that main() executes cleanly and returns exit code 0."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    exit_code = main()
    assert exit_code == 0


def test_main_execution_config_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that main() exits with error code 1 and outputs error message when config is invalid."""
    monkeypatch.setenv("APP_ENV", "invalid_env")
    exit_code = main()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Configuration error:" in captured.err
