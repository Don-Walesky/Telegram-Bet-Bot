"""SQLite database connection management and lifecycle."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Union

from telegram_bet_bot.persistence.schema import initialize_database

PathLike = Union[Path, str]


class Database:
    """Manages SQLite database connections and configuration.

    Guarantees:
    - Foreign-key enforcement is enabled on every opened connection.
    - Uses sqlite3.Row row factory for clean named column access.
    - Automatic parent directory creation for file-backed databases.
    - Clean context-managed connection opening and closing.
    - No global mutable state or unmanaged connection pooling.
    """

    DEFAULT_DB_PATH = Path("data/telegram_bet_bot.db")

    def __init__(self, db_path: PathLike | None = None) -> None:
        """Initialize database manager with target filesystem path or in-memory specifier."""
        if db_path is None:
            self._db_path = self.DEFAULT_DB_PATH
        elif isinstance(db_path, str) and db_path == ":memory:":
            self._db_path = ":memory:"
        else:
            self._db_path = Path(db_path)

    @property
    def db_path(self) -> PathLike:
        """Return the configured database path."""
        return self._db_path

    def _prepare_path(self) -> str:
        """Ensure parent directory exists for file paths and return connection string."""
        if isinstance(self._db_path, Path):
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            return str(self._db_path)
        return str(self._db_path)

    def connect(self) -> sqlite3.Connection:
        """Open, configure, and return a new SQLite connection.

        Enforces PRAGMA foreign_keys = ON and configures Row row_factory.
        Caller is responsible for closing the connection or using connection().
        """
        conn_str = self._prepare_path()
        conn = sqlite3.connect(conn_str)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Context manager yielding an open, foreign-key enforced connection.

        Automatically closes the connection upon context exit.
        """
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self, conn: sqlite3.Connection | None = None) -> Iterator[sqlite3.Connection]:
        """Context manager executing statements within an explicit transaction.

        If a connection is provided, transaction context is managed on that connection.
        If no connection is provided, a new connection is opened, used, committed/rolled back,
        and closed cleanly.
        """
        if conn is not None:
            with conn:
                yield conn
        else:
            with self.connection() as managed_conn:
                with managed_conn:
                    yield managed_conn

    def initialize(self) -> None:
        """Initialize the database schema idempotently."""
        with self.connection() as conn:
            initialize_database(conn)
